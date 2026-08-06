import { Badge, Card } from "../../../components/design-system";
import type { ProductRecord } from "../productAnalytics.types";

type ProductTableProps = {
  products: ProductRecord[];
  onSelect: (product: ProductRecord) => void;
};

export function ProductTable({ products, onSelect }: ProductTableProps) {
  return (
    <Card>
      <div className="product-analytics__section-header">
        <div>
          <p className="product-analytics__kicker">Catalog</p>
          <h2>Product Table</h2>
        </div>
        <Badge tone="info">{products.length} products</Badge>
      </div>
      <div className="product-analytics__table-scroll">
        <table className="product-analytics__table">
          <thead>
            <tr>
              <th scope="col">Product</th>
              <th scope="col">Category</th>
              <th scope="col">Total</th>
              <th scope="col">Active</th>
              <th scope="col">Pending Removal</th>
              <th scope="col">Finalized</th>
              <th scope="col">Pass Rate</th>
              <th scope="col">Health</th>
              <th scope="col">Status</th>
              <th scope="col">Last Updated</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {products.map((product) => (
              <tr key={product.id} className="product-analytics__row" onClick={() => onSelect(product)}>
                <td className="product-analytics__strong">{product.product}</td>
                <td>{product.category}</td>
                <td>{product.totalBatteries}</td>
                <td>{product.activeBatteries}</td>
                <td>{product.pendingRemoval}</td>
                <td>{product.finalized}</td>
                <td>{product.passRate}%</td>
                <td>{product.healthScore}/100</td>
                <td>
                  <Badge tone={product.statusTone}>{product.status}</Badge>
                </td>
                <td>{product.lastUpdated}</td>
                <td>
                  <button
                    className="product-analytics__button"
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onSelect(product);
                    }}
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
