```swift
import UIKit
import Kingfisher

protocol ImageLoadable {
    func loadImage(from url: String)
}

extension ImageLoadable where Self: UIImageView {
    func loadImage(from url: String) {
        let url = URL(string: url)
        self.kf.setImage(with: url)
    }
}

class ViewController: UIViewController {
    @IBOutlet weak var imageView: UIImageView!
    
    override func viewDidLoad() {
        super.viewDidLoad()
        imageView.loadImage(from: "https://example.com/image.jpg")
    }
}

extension UIImageView: ImageLoadable {}
```