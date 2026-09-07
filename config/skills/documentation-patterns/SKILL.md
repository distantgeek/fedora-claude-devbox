---
name: documentation-patterns
description: Documentation generation standards per language — JSDoc, docstrings, rustdoc, godoc, doxygen
compatibility: opencode
---
## Documentation By Language

### Python (docstrings — Google Style)
```python
def process_order(order_id: str, items: list[Item]) -> Order:
    """Processes an order and returns the finalized order object.

    Validates inventory, calculates totals including tax, and
    initiates payment capture. Does NOT send confirmation email.

    Args:
        order_id: Unique order identifier (UUID v4 format).
        items: List of validated Item objects. Must not be empty.

    Returns:
        Order object with status='confirmed' and assigned tracking ID.

    Raises:
        InventoryError: If any item is out of stock.
        PaymentError: If payment capture fails.
        ValueError: If order_id is malformed or items is empty.

    Example:
        >>> items = [Item(sku="ABC-123", qty=2)]
        >>> order = process_order(uuid4(), items)
        >>> order.status
        'confirmed'
    """
```

### Rust (rustdoc)
```rust
/// Processes an order and returns the finalized order.
///
/// Validates inventory, calculates totals including tax, and
/// initiates payment capture. Does NOT send confirmation email.
///
/// # Arguments
/// * `order_id` - Unique order identifier (UUID format).
/// * `items` - Validated items. Must not be empty.
///
/// # Returns
/// `Order` with `status = Confirmed` and assigned tracking ID.
///
/// # Errors
/// Returns `InventoryError` if any item is out of stock.
/// Returns `PaymentError` if payment capture fails.
///
/// # Examples
/// ```
/// let items = vec![Item::new("ABC-123", 2)];
/// let order = process_order(Uuid::new_v4(), items)?;
/// assert_eq!(order.status, Status::Confirmed);
/// ```
pub fn process_order(order_id: Uuid, items: Vec<Item>) -> Result<Order> { }
```

### JavaScript/TypeScript (JSDoc)
```typescript
/**
 * Processes an order and returns the finalized order.
 *
 * Validates inventory, calculates totals including tax, and
 * initiates payment capture. Does NOT send confirmation email.
 *
 * @param orderId - Unique order identifier (UUID v4 format).
 * @param items - Validated item objects. Must not be empty.
 * @returns Order with status 'confirmed' and assigned tracking ID.
 * @throws {InventoryError} If any item is out of stock.
 * @throws {PaymentError} If payment capture fails.
 *
 * @example
 * const items = [{ sku: "ABC-123", qty: 2 }];
 * const order = await processOrder(uuidv4(), items);
 * console.log(order.status); // 'confirmed'
 */
async function processOrder(orderId: string, items: Item[]): Promise<Order> { }
```

### Go (godoc)
```go
// ProcessOrder validates inventory, calculates totals including tax,
// and initiates payment capture for the given order items.
//
// It does NOT send a confirmation email — that is handled by the
// notification service separately.
//
// Errors:
//   - ErrInventory if any item is out of stock
//   - ErrPayment if payment capture fails
//
// Example:
//   order, err := ProcessOrder(ctx, uuid.New(), items)
//   if err != nil {
//       log.Fatal(err)
//   }
//   fmt.Println(order.Status) // "confirmed"
func ProcessOrder(ctx context.Context, orderID uuid.UUID, items []Item) (*Order, error) { }
```

## README.md Checklist
- [ ] Project name and one-line description
- [ ] Prerequisites (language version, tools, system deps)
- [ ] Quick start (clone, install, run)
- [ ] Build command
- [ ] Test command
- [ ] Configuration reference (env vars, config files)
- [ ] Architecture overview (link to docs/architecture.md if complex)
- [ ] API reference link
- [ ] Contributing guide link

## When to Document
- Every public API
- Every configuration option
- Every error type the caller must handle
- Architecture decisions (ADRs in docs/adrs/)
