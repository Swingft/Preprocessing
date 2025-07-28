```swift
import Alamofire

struct Response: Decodable {
    let result: String
}

final class NetworkManager {
    static let shared = NetworkManager()
    
    private init() {}
    
    func request(url: String, method: HTTPMethod = .get, parameters: Parameters? = nil, encoding: ParameterEncoding = URLEncoding.default, headers: HTTPHeaders? = nil, completion: @escaping (Response?, Error?) -> Void) {

        AF.request(url, method: method, parameters: parameters, encoding: encoding, headers: headers).responseDecodable { (response: DataResponse<Response, AFError>) in
            
            switch response.result {
            case .success(let value):
                completion(value, nil)
            case .failure(let error):
                completion(nil, error)
            }
        }
    }
}

```

In the above code Alamofire is being used to perform a network request. The response of the request is assumed to be decodable into an instance of the 'Response' struct. GetLastError() is a method of the 'NetworkManager' singleton class that allows for the result of this network request to be returned. The network request can be customized with different http methods, parameters, encoding types and headers.