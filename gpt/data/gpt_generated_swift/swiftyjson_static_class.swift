```swift
import SwiftyJSON

struct JSONHandler {
    
    static func parseJSON(_ data: Data) {
        let json = try! JSON(data: data)
        let name = json["name"].stringValue
        print(name)
    }
    
    static func createJSON() -> Data {
        let json = JSON(["name": "John Doe"])
        let data = try! json.rawData()
        return data
    }
}

// Calling the static methods
let jsonData = JSONHandler.createJSON()
JSONHandler.parseJSON(jsonData)
```