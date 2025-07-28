```
import UIKit
import Kingfisher

struct ImageModel {
    let url: String
}

class ViewController: UIViewController {
    @IBOutlet weak var imageView: UIImageView!
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        let imageModel = ImageModel(url: "https://example.com/image.jpg")
        ImageLoader.load(from: imageModel.url, into: imageView)
    }
}

class ImageLoader {
    
    static func load(from urlString: String, into imageView: UIImageView) {
        guard let url = URL(string: urlString) else { return }
        imageView.kf.setImage(with: url)
    }
}
```