```Swift
import Alamofire

class MyNetworkingClass {

    var URLString: String {
        return "https://example.com"
    }

    func makeRequest() {
        Alamofire.request(URLString).responseJSON { response in
            if let json = response.result.value {
                print("JSON: \(json)")
            }
        }
    }
}
```