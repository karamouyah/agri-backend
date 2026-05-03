# Old vs New Database Refactor Plan

## Step 1: Compare old database vs new database

### Old database (current project, Django apps)
- `users.User` is the main identity table with role/status/approval fields.
- Role profiles exist as `FarmerProfile`, `BuyerProfile`, `TransporterProfile`.
- Product domain:
  - `catalog.Category`
  - `catalog.Product` (includes farmer, price, quantity, quality, status, image, description)
  - `catalog.OfficialPrice` is 1:1 per category.
- Order domain:
  - `orders.Order`, `orders.OrderItem`, `orders.Invoice`
- Logistics domain:
  - `logistics.Mission` linked to order/transporter.

### New database (target, SQL)
- Person-centric user model:
  - `Person`, then role tables `Farmer`, `Buyer`, `Admin`, `Transporter`.
- Separate farm catalog structure:
  - `Farm`, `Category`, `Product`, `ProductList`, `Season`, `OfficialPrice`
- Order/fulfillment/payment/review:
  - `Orders`, `OrderItem`, `Payments`, `Shipment`, `TransporterReview`, `ItemReview`
- Onboarding workflow:
  - `JoinRequest`

### Key structural differences
- Current auth model is single-table user + profile, target is `Person` + role-specific tables.
- Current `Product` stores price and stock directly; target moves transactional price/quantity to `ProductList`.
- Current logistics uses `Mission`; target uses `Shipment`.
- Current invoices are not in target schema and must be removed or transformed.
- Current ministry approval fields (`status`, `approval_status`) must be mapped to integer `Status`/`Role` codes in `Person` and `JoinRequest`.

## Step 2: List all required changes

1. Replace Django model layer with the target relational model:
   - Remove old model dependencies in `users`, `catalog`, `orders`, `logistics`.
   - Create models/tables matching:
     - `Person`, `Farmer`, `Buyer`, `Admin`, `Transporter`
     - `Farm`, `Category`, `Product`, `Season`, `OfficialPrice`, `ProductList`
     - `Orders`, `OrderItem`, `Payments`, `Shipment`, `TransporterReview`, `ItemReview`, `JoinRequest`
2. Authentication refactor:
   - Login by `Person.Username`/`Person.Email` + `Person.Password`.
   - Role resolution from role tables or `Person.Role`.
   - Approval gating through `Person.Status` and/or `JoinRequest.Status`.
3. API DTO/serializer refactor:
   - Replace old fields (`farm_name`, `quality`, `invoice`, `mission`, etc.) with target schema fields.
4. Query and repository refactor:
   - Replace joins on old tables with joins between `Person` and role tables.
   - Replace order/product joins to use `ProductList`, `Orders`, `OrderItem`, `Shipment`.
5. Validation changes:
   - Farmer farm uniqueness should be enforced via:
     - unique constraint at DB layer (recommended on `Farm.Location` or dedicated normalized farm address field),
     - plus service-level check.
6. Remove conflicting obsolete logic:
   - Remove `Invoice` workflows or map to `Payments`.
   - Remove `Mission` workflows and replace with `Shipment`.
7. Admin/ministry features:
   - Implement pending request listing from `JoinRequest`.
   - Approve/reject should create/update `Person` + role rows accordingly.

## Step 3: Provide the updated final database schema

- Final schema SQL is provided in:
  - `backend/sql/new_schema.sql`
- Legacy-to-new data migration helper is provided in:
  - `backend/sql/migrate_old_to_new.sql`

## Step 4: Show backend/code changes required

### Files/modules to replace
- `backend/apps/users/models.py`
- `backend/apps/catalog/models.py`
- `backend/apps/orders/models.py`
- `backend/apps/logistics/models.py`
- Related serializers/views/urls in:
  - `backend/apps/users/`
  - `backend/apps/catalog/`
  - `backend/apps/orders/`
  - `backend/apps/logistics/`

### Required implementation direction
1. Create a new persistence layer aligned to table names/columns exactly.
2. Replace ORM objects and serializer fields:
   - `User` -> `Person` + role table mapping
   - `Order` -> `Orders`
   - `Mission` -> `Shipment`
   - `Invoice` -> `Payments`
3. Update all services/controllers:
   - auth register/login/approval
   - product listing
   - checkout/order placement
   - shipment assignment and tracking
   - reviews and rating summaries
4. Update admin endpoints:
   - pending join requests
   - approve/reject
   - account status changes
5. Update frontend API contracts for renamed fields and entities.

## Step 5: Migration notes if needed

### Data migration strategy (recommended phased)
1. Create all new tables (done in `backend/sql/new_schema.sql`).
2. Run `backend/sql/migrate_old_to_new.sql` on a staging copy.
3. Validate entity counts and foreign key consistency.
4. Backfill missing business-specific values (ratings, review text, shipping fees, etc.).
5. Cut over application reads/writes to new tables.
6. Remove old tables only after verification.

### Safety controls
- Run migration in staging with snapshots.
- Validate FK integrity and row counts.
- Use id-mapping tables during migration to preserve relationships.
