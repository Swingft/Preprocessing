import CryptoKit
import Foundation

struct PasswordHasher {
    static let saltLength = 32
    static let iterations = 100_000
    static let keyLength = 32
    
    static func hashPassword(_ password: String) throws -> (salt: Data, hash: Data) {
        let salt = try generateRandomSalt()
        let hash = try deriveKeyFromPassword(password, salt: salt)
        return (salt, hash)
    }
    
    static func generateRandomSalt() throws -> Data {
        var salt = Data(count: saltLength)
        let result = salt.withUnsafeMutableBytes { bytes in
            SecRandomCopyBytes(kSecRandomDefault, saltLength, bytes.baseAddress!)
        }
        
        guard result == errSecSuccess else {
            throw NSError(domain: "PasswordHasher", code: result)
        }
        
        return salt
    }
    
    static func deriveKeyFromPassword(_ password: String, salt: Data) throws -> Data {
        guard let passwordData = password.data(using: .utf8) else {
            throw NSError(domain: "PasswordHasher", code: -1, userInfo: [NSLocalizedDescriptionKey: "Password encoding failed"])
        }
        
        var derivedKey = Data(count: keyLength)
        let result = derivedKey.withUnsafeMutableBytes { derivedKeyBytes in
            salt.withUnsafeBytes { saltBytes in
                passwordData.withUnsafeBytes { passwordBytes in
                    CCKeyDerivationPBKDF(
                        CCPBKDFAlgorithm(kCCPBKDF2),
                        passwordBytes.baseAddress?.assumingMemoryBound(to: Int8.self),
                        passwordData.count,
                        saltBytes.baseAddress?.assumingMemoryBound(to: UInt8.self),
                        salt.count,
                        CCPBKDFAlgorithm(kCCPRFHmacAlgSHA256),
                        UInt32(iterations),
                        derivedKeyBytes.baseAddress?.assumingMemoryBound(to: UInt8.self),
                        keyLength
                    )
                }
            }
        }
        
        guard result == kCCSuccess else {
            throw NSError(domain: "PasswordHasher", code: Int(result))
        }
        
        return derivedKey
    }
    
    static func verifyPassword(_ password: String, againstHash storedHash: Data, withSalt salt: Data) throws -> Bool {
        let computedHash = try deriveKeyFromPassword(password, salt: salt)
        return computedHash == storedHash
    }
}