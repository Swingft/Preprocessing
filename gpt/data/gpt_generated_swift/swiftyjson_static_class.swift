```swift
import SwiftyJSON

final class JSONUtil {
    
    static let sharedInstance = JSONUtil()
    
    private init() {}
    
    static func parse(jsonString: String) -> JSON {
        if let dataFromString = jsonString.data(using: .utf8, allowLossyConversion: false) {
            return JSON(data: dataFromString)
        } else {
            return JSON.null
        }
    }
    
    static func getStringValue(json: JSON, key: String) -> String {
        let result = json[key].stringValue
        return result
    }
    
    static func getIntValue(json: JSON, key: String) -> Int {
        let result = json[key].intValue
        return result
    }
}
```