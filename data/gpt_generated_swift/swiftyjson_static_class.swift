```swift
import SwiftyJSON

class JsonUtils {
    
    static func parse(jsonString: String) -> JSON {
        if let data = jsonString.data(using: .utf8) {
            return try! JSON(data: data)
        }
        return JSON.null
    }
    
    static func extractValue(json: JSON, key: String) -> String {
        if let value = json[key].string {
            return value
        }
        return ""
    }
}

let jsonString = "{\"name\":\"John\",\"age\":30,\"city\":\"New York\"}"

let parsedJson = JsonUtils.parse(jsonString: jsonString)

let name = JsonUtils.extractValue(json: parsedJson, key: "name")
let age = JsonUtils.extractValue(json: parsedJson, key: "age")
let city = JsonUtils.extractValue(json: parsedJson, key: "city")

print(name)
print(age)
print(city)
```