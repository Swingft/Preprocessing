```swift
import Alamofire

class NetworkManager {

    var baseURL: String {
        return "https://api.example.com/"
    }

    func fetchSomeData(endpoint: String) {
        Alamofire.request(self.baseURL + endpoint).responseJSON { response in
            guard response.result.isSuccess else {
                print("Error while fetching remote rooms: \(String(describing: response.result.error))")
                return
            }
            
            guard let value = response.result.value as? [String: Any] else {
                print("Malformed data received from fetchAllRooms service")
                return
            }
            
            print("Data received: \(value)")
        }
    }
}
```