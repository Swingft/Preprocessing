```swift
import UIKit
import Kingfisher

class ImageLoader {
    
    static let shared = ImageLoader()
    
    private init() {}
    
    func loadImage(url: String, imageView: UIImageView) {
        let url = URL(string: url)
        imageView.kf.setImage(with: url)
    }
}

class ViewController: UIViewController {

   @IBOutlet weak var imageView: UIImageView!
   
   override func viewDidLoad() {
       super.viewDidLoad()
       
       let imageURL = "https://example.com/image.jpg"
       ImageLoader.shared.loadImage(url: imageURL, imageView: imageView)
   }
}
```