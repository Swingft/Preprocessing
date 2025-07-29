import SwiftyJSON

class NetworkManager {
    static let shared = NetworkManager()
    private init() {}
    
    static func parseUserData(json: JSON) -> User? {
        guard let name = json["name"].string,
              let age = json["age"].int,
              let email = json["email"].string else {
            return nil
        }
        
        let address = json["address"]
        let street = address["street"].stringValue
        let city = address["city"].stringValue
        let country = address["country"].stringValue
        
        let hobbies = json["hobbies"].arrayValue.map { $0.stringValue }
        
        return User(name: name,
                   age: age,
                   email: email,
                   address: Address(street: street,
                                  city: city,
                                  country: country),
                   hobbies: hobbies)
    }
    
    static func processJSONData(_ jsonString: String) -> [User] {
        guard let data = jsonString.data(using: .utf8) else { return [] }
        let json = try? JSON(data: data)
        var users: [User] = []
        
        if let usersArray = json?["users"].array {
            for userJSON in usersArray {
                if let user = parseUserData(json: userJSON) {
                    users.append(user)
                }
            }
        }
        
        return users
    }
}

struct User {
    let name: String
    let age: Int
    let email: String
    let address: Address
    let hobbies: [String]
}

struct Address {
    let street: String
    let city: String
    let country: String
}