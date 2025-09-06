import Security
import LocalAuthentication

final class SecureTokenManager {
    static let shared = SecureTokenManager()
    private let keychainService = "com.myapp.auth"
    private let tokenKey = "userAuthToken"
    private let context = LAContext()
    
    private init() {}
    
    func saveToken(_ token: String) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: tokenKey,
            kSecValueData as String: token.data(using: .utf8)!,
            kSecAttrAccessControl as String: try generateAccessControl(),
            kSecUseAuthenticationUI as String: kSecUseAuthenticationUIAllow
        ]
        
        let status = SecItemAdd(query as CFDictionary, nil)
        
        if status == errSecDuplicateItem {
            try updateToken(token)
        } else if status != errSecSuccess {
            throw KeychainError.saveError(status: status)
        }
    }
    
    func retrieveToken() throws -> String {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: tokenKey,
            kSecMatchLimit as String: kSecMatchLimitOne,
            kSecReturnData as String: true,
            kSecUseAuthenticationUI as String: kSecUseAuthenticationUIAllow
        ]
        
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        
        guard status == errSecSuccess,
              let data = result as? Data,
              let token = String(data: data, encoding: .utf8) else {
            throw KeychainError.retrieveError(status: status)
        }
        
        return token
    }
    
    private func updateToken(_ token: String) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: tokenKey
        ]
        
        let attributes: [String: Any] = [
            kSecValueData as String: token.data(using: .utf8)!
        ]
        
        let status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        
        if status != errSecSuccess {
            throw KeychainError.updateError(status: status)
        }
    }
    
    private func generateAccessControl() throws -> SecAccessControl {
        guard let accessControl = SecAccessControlCreateWithFlags(
            nil,
            kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly,
            .biometryAny,
            nil
        ) else {
            throw KeychainError.accessControlError
        }
        return accessControl
    }
}

enum KeychainError: Error {
    case saveError(status: OSStatus)
    case retrieveError(status: OSStatus)
    case updateError(status: OSStatus)
    case accessControlError
}