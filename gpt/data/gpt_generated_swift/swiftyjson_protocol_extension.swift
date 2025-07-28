```swift
import SwiftyJSON

protocol JSONInitializable {
    init?(json: JSON)
}

extension JSONInitializable where Self: NSObject {

    init?(jsonString: String) {
        if let data = jsonString.data(using: .utf8) {
            let json = JSON(data)
            self.init(json: json)
        } else {
            return nil
        }
    }
}

class User: NSObject, JSONInitializable {
    var name: String?
    var email: String?

    required init?(json: JSON) {
        self.name = json["name"].string
        self.email = json["email"].string
        super.init()

        if self.name == nil || self.email == nil {
            return nil
        }
    }
}

let jsonString = """
{
    "name" : "John Doe",
    "email" : "john@doe.com"
}
"""

if let user = User(jsonString: jsonString) {
    print(user.name)   // Output: John Doe
    print(user.email)  // Output: john@doe.com
}
```