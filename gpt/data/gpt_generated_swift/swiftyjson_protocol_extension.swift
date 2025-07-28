```swift
import SwiftyJSON

protocol Serializable {
    init?(json: JSON)
}

extension Serializable {
    static func decode(_ json: JSON) -> Self? {
        if json.isNull {
            return nil
        } else {
            return Self.init(json: json)
        }
    }
}

struct User: Serializable {
    let name: String
    let email: String

    init?(json: JSON) {
        guard let name = json["name"].string, let email = json["email"].string else {
            return nil
        }

        self.name = name
        self.email = email
    }
}

let jsonString = """
{
    "name": "John Doe",
    "email": "john@example.com"
}
"""

if let dataFromString = jsonString.data(using: .utf8, allowLossyConversion: false), let user = User.decode(JSON(dataFromString)) {
    print(user.name)
    print(user.email)
}
```