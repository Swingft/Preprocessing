```swift
import Foundation
import SwiftyJSON

class MyJSONHandler {
    static func parseJSON(data: Data) -> JSON {
        let json = try! JSON(data: data)
        return json
    }
}
```