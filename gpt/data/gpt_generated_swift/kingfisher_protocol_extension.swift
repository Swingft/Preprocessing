```swift
import UIKit
import Kingfisher

protocol ImageLoadable {
    var imageUrl: URL? { get }
    var imagePlaceholder: UIImage? { get }
    var imageView: UIImageView { get }
}

extension ImageLoadable {
    
    func loadImage() {
        imageView.kf.setImage(with: imageUrl, placeholder: imagePlaceholder)
    }
}

class CustomImageCell: UITableViewCell, ImageLoadable {
    
    @IBOutlet weak var customImageView: UIImageView!
    
    var imageUrl: URL? {
        return URL(string: "https://example.com/image.jpg")
    }
    
    var imagePlaceholder: UIImage? {
        return UIImage(named: "placeholder")
    }
    
    var imageView: UIImageView {
        return customImageView
    }
    
    override func awakeFromNib() {
        super.awakeFromNib()
        loadImage()
    }
}
```