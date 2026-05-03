-- Data migration helper: current Django schema -> target new schema
-- IMPORTANT:
-- 1) Run on a backup copy first.
-- 2) Validate table names in your DB before execution.
-- 3) This script assumes target tables from new_schema.sql already exist.

BEGIN TRANSACTION;

-- -----------------------------------------------------------------------------
-- 1) Person
-- -----------------------------------------------------------------------------
INSERT INTO Person (
    IDPerson,
    FirstName,
    LastName,
    Address,
    PhoneNumber,
    personalPictureURL,
    DocumentsURL,
    Email,
    Username,
    Password,
    Status,
    Role
)
SELECT
    u.id AS IDPerson,
    u.first_name AS FirstName,
    u.last_name AS LastName,
    COALESCE(bp.address, u.address, fp.farm_address, u.location, '') AS Address,
    COALESCE(fp.phone_number, tp.phone_number, bp.phone_number, u.phone, '') AS PhoneNumber,
    '' AS personalPictureURL,
    '' AS DocumentsURL,
    u.email AS Email,
    u.username AS Username,
    u.password AS Password,
    CASE
        WHEN u.approval_status = 'approved' THEN 1
        WHEN u.approval_status = 'pending' THEN 0
        WHEN u.approval_status = 'rejected' THEN 2
        ELSE 0
    END AS Status,
    CASE
        WHEN u.role = 'farmer' THEN 1
        WHEN u.role = 'buyer' THEN 2
        WHEN u.role = 'transporter' THEN 3
        WHEN u.role = 'ministry' THEN 4
        ELSE 0
    END AS Role
FROM users_user u
LEFT JOIN users_farmerprofile fp ON fp.user_id = u.id
LEFT JOIN users_transporterprofile tp ON tp.user_id = u.id
LEFT JOIN users_buyerprofile bp ON bp.user_id = u.id;

-- -----------------------------------------------------------------------------
-- 2) Role tables
-- -----------------------------------------------------------------------------
INSERT INTO Farmer (IDFarmer, IDPerson, AverageRating, TotalReviews)
SELECT
    u.id AS IDFarmer,
    u.id AS IDPerson,
    NULL AS AverageRating,
    NULL AS TotalReviews
FROM users_user u
WHERE u.role = 'farmer';

INSERT INTO Buyer (IDBuyer, IDPerson)
SELECT
    u.id AS IDBuyer,
    u.id AS IDPerson
FROM users_user u
WHERE u.role = 'buyer';

INSERT INTO Admin (IDAdmin, IDPerson, TotalProcesses, RegionCode)
SELECT
    u.id AS IDAdmin,
    u.id AS IDPerson,
    0 AS TotalProcesses,
    NULL AS RegionCode
FROM users_user u
WHERE u.role = 'ministry';

INSERT INTO Transporter (
    IDTransporter,
    IDPerson,
    Capacity,
    ServiceArea,
    VehicleType,
    AverageRating,
    TotalReviews
)
SELECT
    u.id AS IDTransporter,
    u.id AS IDPerson,
    NULL AS Capacity,
    '' AS ServiceArea,
    COALESCE(tp.vehicle, u.vehicle, '') AS VehicleType,
    NULL AS AverageRating,
    NULL AS TotalReviews
FROM users_user u
LEFT JOIN users_transporterprofile tp ON tp.user_id = u.id
WHERE u.role = 'transporter';

-- -----------------------------------------------------------------------------
-- 3) Farm
-- -----------------------------------------------------------------------------
INSERT INTO Farm (IDFarm, IDFarmer, Location, Name, Area)
SELECT
    u.id AS IDFarm,
    u.id AS IDFarmer,
    COALESCE(u.location, fp.farm_address, '') AS Location,
    COALESCE(u.farm_name, 'Farm #' || u.id) AS Name,
    NULL AS Area
FROM users_user u
LEFT JOIN users_farmerprofile fp ON fp.user_id = u.id
WHERE u.role = 'farmer';

-- -----------------------------------------------------------------------------
-- 4) Category / Product / ProductList
-- -----------------------------------------------------------------------------
INSERT INTO Category (IDCategory, Name)
SELECT c.id, c.name
FROM catalog_category c;

INSERT INTO Product (IDProduct, Name, IDCategory)
SELECT p.id, p.name, p.category_id
FROM catalog_product p;

INSERT INTO ProductList (IDProductList, IDProduct, IDFarmer, Quantity, Price)
SELECT
    p.id AS IDProductList,
    p.id AS IDProduct,
    p.farmer_id AS IDFarmer,
    p.quantity_available AS Quantity,
    CAST(p.price AS INT) AS Price
FROM catalog_product p;

-- -----------------------------------------------------------------------------
-- 5) Season / OfficialPrice (best-effort mapping)
-- -----------------------------------------------------------------------------
INSERT INTO Season (IDSeason, Name)
VALUES (1, 'Default')
ON CONFLICT(IDSeason) DO NOTHING;

INSERT INTO OfficialPrice (IDOfficialPrice, MaxPrice, IDSeason, IDProduct, IDAdmin)
SELECT
    op.id AS IDOfficialPrice,
    CAST(op.maximum AS INT) AS MaxPrice,
    1 AS IDSeason,
    (
        SELECT p.id
        FROM catalog_product p
        WHERE p.category_id = op.category_id
        ORDER BY p.id
        LIMIT 1
    ) AS IDProduct,
    (
        SELECT a.id
        FROM users_user a
        WHERE a.role = 'ministry'
        ORDER BY a.id
        LIMIT 1
    ) AS IDAdmin
FROM catalog_officialprice op;

-- -----------------------------------------------------------------------------
-- 6) Orders / OrderItem
-- -----------------------------------------------------------------------------
INSERT INTO Orders (
    IDOrder,
    IDBuyer,
    IDFarmer,
    TotalAmount,
    OrderDate,
    Status,
    DeliveryAddress,
    PickupAddress
)
SELECT
    o.id AS IDOrder,
    o.buyer_id AS IDBuyer,
    o.farmer_id AS IDFarmer,
    COALESCE(SUM(CAST(oi.quantity * oi.unit_price AS INT)), 0) AS TotalAmount,
    o.created_at AS OrderDate,
    CASE
        WHEN o.status = 'pending' THEN 0
        WHEN o.status = 'accepted' THEN 1
        WHEN o.status = 'declined' THEN 2
        WHEN o.status = 'shipped' THEN 3
        WHEN o.status = 'in transit' THEN 4
        WHEN o.status = 'delivered' THEN 5
        ELSE 0
    END AS Status,
    o.address AS DeliveryAddress,
    (
        SELECT f.Location
        FROM Farm f
        WHERE f.IDFarmer = o.farmer_id
        LIMIT 1
    ) AS PickupAddress
FROM orders_order o
LEFT JOIN orders_orderitem oi ON oi.order_id = o.id
GROUP BY o.id, o.buyer_id, o.farmer_id, o.created_at, o.status, o.address;

INSERT INTO OrderItem (
    IDOrderItem,
    IDOrder,
    IDProductList,
    Quantity,
    Price,
    TotalItemsPrice
)
SELECT
    oi.id AS IDOrderItem,
    oi.order_id AS IDOrder,
    oi.product_id AS IDProductList,
    oi.quantity AS Quantity,
    CAST(oi.unit_price AS INT) AS Price,
    CAST(oi.quantity * oi.unit_price AS INT) AS TotalItemsPrice
FROM orders_orderitem oi;

-- -----------------------------------------------------------------------------
-- 7) Payments (mapped from legacy invoices)
-- -----------------------------------------------------------------------------
INSERT INTO Payments (
    IDPayment,
    IDOrder,
    Amount,
    PaymentMethod,
    TransactionDate
)
SELECT
    i.id AS IDPayment,
    i.order_id AS IDOrder,
    CAST(i.amount AS INT) AS Amount,
    'legacy_invoice' AS PaymentMethod,
    i.created_at AS TransactionDate
FROM orders_invoice i;

-- -----------------------------------------------------------------------------
-- 8) Shipment (mapped from logistics missions)
-- -----------------------------------------------------------------------------
INSERT INTO Shipment (
    IDShipping,
    IDOrder,
    IDTransporter,
    TrackingNumber,
    Status,
    ShippingFee,
    PickupDate,
    EstimatedDeliveryDate,
    ActualDeliveryDate
)
SELECT
    m.id AS IDShipping,
    m.order_id AS IDOrder,
    m.transporter_id AS IDTransporter,
    m.mission_id AS TrackingNumber,
    CASE
        WHEN m.status = 'pending' THEN 0
        WHEN m.status = 'accepted' THEN 1
        WHEN m.status = 'declined' THEN 2
        WHEN m.status = 'picked up' THEN 3
        WHEN m.status = 'in transit' THEN 4
        WHEN m.status = 'delivered' THEN 5
        ELSE 0
    END AS Status,
    0 AS ShippingFee,
    m.created_at AS PickupDate,
    m.deadline AS EstimatedDeliveryDate,
    NULL AS ActualDeliveryDate
FROM logistics_mission m;

-- -----------------------------------------------------------------------------
-- 9) JoinRequest (from pending users)
-- -----------------------------------------------------------------------------
INSERT INTO JoinRequest (
    IDRequest,
    IDAdmin,
    FirstName,
    LastName,
    Email,
    PhoneNumber,
    Address,
    RequestedRole,
    personalPictureURL,
    DocumentsURL,
    RequestDate,
    ReviewDate,
    Notes,
    Status
)
SELECT
    u.id AS IDRequest,
    (
        SELECT a.id
        FROM users_user a
        WHERE a.role = 'ministry'
        ORDER BY a.id
        LIMIT 1
    ) AS IDAdmin,
    u.first_name AS FirstName,
    u.last_name AS LastName,
    u.email AS Email,
    COALESCE(fp.phone_number, tp.phone_number, bp.phone_number, u.phone, '') AS PhoneNumber,
    COALESCE(bp.address, fp.farm_address, u.address, u.location, '') AS Address,
    CASE
        WHEN u.role = 'farmer' THEN 1
        WHEN u.role = 'buyer' THEN 2
        WHEN u.role = 'transporter' THEN 3
        ELSE 0
    END AS RequestedRole,
    '' AS personalPictureURL,
    '' AS DocumentsURL,
    u.date_joined AS RequestDate,
    NULL AS ReviewDate,
    'Migrated from legacy approval queue' AS Notes,
    0 AS Status
FROM users_user u
LEFT JOIN users_farmerprofile fp ON fp.user_id = u.id
LEFT JOIN users_transporterprofile tp ON tp.user_id = u.id
LEFT JOIN users_buyerprofile bp ON bp.user_id = u.id
WHERE u.approval_status = 'pending';

COMMIT;
