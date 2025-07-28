```swift
import Foundation
import SwiftyJSON

final class JSONHandler {
    
    static let sharedInstance = JSONHandler()
    
    private init() {}
    
    func parseJSON(_ data: Data) -> JSON {
        let json = try! JSON(data: data)
        return json
    }
    
    func stringFromJSON(_ json: JSON, key: String) -> String {
        if let string = json[key].string {
            return string
        } else {
            return ""
        }
    }

    static func integerFromJSON(_ json: JSON, key: String) -> Int {
        if let integer = json[key].int {
            return integer
        } else {
            return 0
        }
    }

    static func doubleFromJSON(_ json: JSON, key: String) -> Double {
        if let double = json[key].double {
            return double
        } else {
            return 0.0
        }
    }

    static func boolFromJSON(_ json: JSON, key: String) -> Bool {
        if let boolean = json[key].bool {
            return boolean
        } else {
            return false
        }
    }
}
```