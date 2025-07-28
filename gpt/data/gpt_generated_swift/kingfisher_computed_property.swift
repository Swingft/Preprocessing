```swift
import UIKit
import Kingfisher

class ExampleViewController: UIViewController {
    
    @IBOutlet weak var imageView: UIImageView!
    
    var imageURL: String? {
        didSet {
            self.updateImage()
        }
    }
    
    // Use Kingfisher to download and cache image from url
    private func updateImage() {
        guard let urlStr = self.imageURL, let url = URL(string: urlStr) else { return }
        self.imageView.kf.setImage(with: url)
    }
}
```