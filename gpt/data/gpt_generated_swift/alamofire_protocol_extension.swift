```swift
import Alamofire

protocol DataRequestProtocol {
    func requestData(url: String, method: HTTPMethod, parameters: [String: Any]?, headers: [String: String]?)
}

extension DataRequestProtocol {
    
    func requestData(url: String, method: HTTPMethod = .get, parameters: [String: Any]? = nil, headers: [String: String]? = nil) {
        Alamofire.request(url, method: method, parameters: parameters, headers: headers).responseJSON { (response) in
            switch response.result {
            case .success:
                print("Request Successful!")
            case .failure(let error):
                print(error)
            }
        }
    }
}

class NetworkRequest: DataRequestProtocol { }

let networkRequest = NetworkRequest()
networkRequest.requestData(url: "http://api.example.com")
```