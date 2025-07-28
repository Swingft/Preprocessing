```swift
import SwiftyJSON

struct User {
    var json: JSON

    var name: String {
        get {
            return self.json["name"].stringValue
        }
    }
    
    var age: Int {
        get {
            return self.json["age"].intValue
        }
    }
    
    init(json: JSON) {
        self.json = json
    }
}

let jsonString = "{\"name\":\"John\", \"age\":30}"

if let data = jsonString.data(using: .utf8) {
    let json = JSON(data)
    let user = User(json: json)
    
    print(user.name) // "John"
    print(user.age) // 30
}
```