import Foundation

extension URLSession: URLSessionDelegate {
    static let pinnedSession: URLSession = {
        let configuration = URLConfiguration.default
        let delegate = PinnedCertificateDelegate()
        return URLSession(configuration: configuration, delegate: delegate, delegateQueue: nil)
    }()
}

final class PinnedCertificateDelegate: NSObject, URLSessionDelegate {
    private let pinnedCertificateData: Data = {
        let certificatePath = Bundle.main.path(forResource: "certificate", ofType: "cer")!
        return try! Data(contentsOf: URL(fileURLWithPath: certificatePath))
    }()
    
    private let trustedDomain = "api.securepayments.example.com"
    
    func urlSession(_ session: URLSession, didReceive challenge: URLAuthenticationChallenge, completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        guard let serverTrust = challenge.protectionSpace.serverTrust,
              let certificate = SecTrustGetCertificateAtIndex(serverTrust, 0),
              challenge.protectionSpace.host == trustedDomain else {
            completionHandler(.cancelAuthenticationChallenge, nil)
            return
        }
        
        let serverCertificateData = SecCertificateCopyData(certificate) as Data
        
        if serverCertificateData == pinnedCertificateData {
            let credential = URLCredential(trust: serverTrust)
            completionHandler(.useCredential, credential)
        } else {
            completionHandler(.cancelAuthenticationChallenge, nil)
        }
    }
}

extension URLRequest {
    static func secureRequest(url: URL) -> URLRequest {
        var request = URLRequest(url: url)
        request.cachePolicy = .reloadIgnoringLocalAndRemoteCacheData
        request.timeoutInterval = 30
        return request
    }
}

extension URLSession {
    func securePinnedDataTask(with request: URLRequest, completionHandler: @escaping (Data?, URLResponse?, Error?) -> Void) -> URLSessionDataTask {
        return URLSession.pinnedSession.dataTask(with: request, completionHandler: completionHandler)
    }
}