```swift
import Alamofire

class NetworkManager {
    static let shared = NetworkManager()
    
    private init() {}

    func getRequest(url: String) {

        Alamofire.request(url).responseJSON { response in 
            print("Request: \(String(describing: response.request))")
            print("Response: \(String(describing: response.response))")
            print("Result: \(response.result)")
            
            if let json = response.result.value {
                print("JSON: \(json)")
            } else {
                print("Data is missing.")
            }
        }
    }

    static func postRequest(url: String, parameters: Parameters) {
        Alamofire.request(url, method: .post, parameters: parameters, encoding: JSONEncoding.default)
            .responseJSON { response in
                print(response)
        }
    }
}
```