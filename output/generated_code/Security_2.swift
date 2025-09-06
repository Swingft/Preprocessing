import Foundation
import CryptoKit

struct AESEncryption {
    private let key: SymmetricKey
    
    init(keyData: Data) throws {
        guard keyData.count == 32 else {
            throw CryptoError.invalidKeySize
        }
        self.key = SymmetricKey(data: keyData)
    }
    
    func encrypt(_ data: Data) throws -> Data {
        let sealedBox = try AES.GCM.seal(data, using: key)
        return sealedBox.combined!
    }
    
    func decrypt(_ encryptedData: Data) throws -> Data {
        let sealedBox = try AES.GCM.SealedBox(combined: encryptedData)
        return try AES.GCM.open(sealedBox, using: key)
    }
    
    enum CryptoError: Error {
        case invalidKeySize
    }
    
    static func generateRandomKey() -> Data {
        let key = SymmetricKey(size: .bits256)
        return key.withUnsafeBytes { Data($0) }
    }
}