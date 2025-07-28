```swift
import Alamofire

protocol ServiceRequester {
    var baseUrl: String { get }
    func request(path: String, method: HTTPMethod, parameters: Parameters?)
}

extension ServiceRequester {
    func request(path: String, method: HTTPMethod = .get, parameters: Parameters? = nil) {
        let url = "\(baseUrl)\(path)"
        Alamofire.request(url, method: method, parameters: parameters).validate().responseJSON { response in
            switch response.result {
            case .success:
                print("Validation Successful")
            case .failure(let error):
                print(error)
            }
        }
    }
}

struct UserService: ServiceRequester {
    let baseUrl = "https://example.com/"

    func getUserDetails(userId: String) {
        request(path: "users/\(userId)")
    }
}
```