```swift
import SwiftyJSON

struct Product {
    let json: JSON

    init(json: JSON) {
        self.json = json
    }
    
    var name: String {
        return json["name"].stringValue
    }

    var price: Double {
        return json["price"].doubleValue
    }
}

let jsonString = """
{
"name": "iPhone X",
"price": 999.99
}
"""

let jsonData = Data(jsonString.utf8)
if let json = try? JSON(data: jsonData) {
    let product = Product(json: json)
    print(product.name)  // "iPhone X"
    print(product.price) // 999.99
}
```