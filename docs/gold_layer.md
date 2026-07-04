# Gold Layer Design

## Objective

The Gold Layer represents the business-ready analytical layer of the ELT pipeline.

Unlike the Bronze Layer (raw landing) and the Silver Layer (cleaned and standardized data), the Gold Layer is designed specifically for business analytics and reporting.

It exposes curated fact tables and conformed dimension tables that provide a consistent, reusable foundation for dashboards, ad-hoc analysis, and future analytical models.

The design follows a dimensional modeling approach to:

- Support fast analytical queries.
- Separate business entities from transactional measures.
- Maintain consistent reporting across multiple datasets.
- Simplify dashboard development.
- Scale as new report types and historical periods are added.

The Gold Layer is built entirely from the Silver Layer, ensuring that all business logic, standardization, validation, and enrichment occur before analytical modeling.

## Design Principles

The Gold Layer follows the principles defined in the project requirements.

### 1. Business-Oriented

The Gold Layer models business concepts rather than raw report structures.

Examples include:

- Orders
- Ordered Items
- Kitchen Performance
- Brand
- Platform
- Date

rather than individual report exports.

---

### 2. Conformed Dimensions

Common business entities such as Brand, Platform, Date, Item, and Category are represented once and shared across all analytical models.

This ensures consistent reporting regardless of the originating report.

---

### 3. Grain Preservation

Each fact table has one clearly defined grain.

Every measure stored within a fact table belongs to that grain.

---

### 4. Incremental

Gold models are generated from incremental Silver data.

New reporting periods extend the warehouse without rebuilding historical data.

---

### 5. Honest Analytics

Only metrics supported by the available data are modeled.

For example:

- Gross Revenue can be calculated.
- Average Order Value can be calculated.
- Kitchen Preparation Time can be calculated.

However:

- Net Profit
- Platform Commission
- Food Cost
- Customer Retention

are intentionally excluded because the source data does not contain the necessary information.

Investigation Findings

The Order Summary report initially appeared to contain duplicate invoice
numbers.

Further investigation showed that invoice numbers are reused across
different restaurant branches.

Example:

Invoice 11465 exists in:

- Chandivali
- Thane
- Parel

Each record represents a different business order with different
timestamps, totals, customers, and KOT numbers.

A second investigation confirmed that the combination

    restaurant_name + invoice_no

is unique within the provided dataset.

Therefore invoice_no is a branch-level business identifier rather than a
globally unique identifier.

The analytical grain for orders is therefore based on the business order
identified by the combination of restaurant and invoice number.

                   Power BI Dashboard
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   Sales Analysis     Kitchen Analysis   Menu Analysis
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                    GOLD WAREHOUSE
                           │
      ┌────────────────────┼────────────────────┐
      │                    │                    │
 FactOrders         FactOrderItems       FactKitchen
      │                    │                    │
      └──────────────┬─────┴─────────────┬──────┘
                     │                   │
      ┌──────────────┼───────────────────┼──────────────┐
      │              │                   │              │
   DimDate      DimBrand          DimPlatform     DimCategory
                                            │
                                         DimItem
                           │
                         SILVER
                           │
                         BRONZE
                           │
                           RAW