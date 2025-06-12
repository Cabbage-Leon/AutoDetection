from PIL import Image, ImageDraw
import os

def create_icon(size):
    # 创建一个新的图像，使用RGBA模式（支持透明度）
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # 计算边框和圆角
    border = size // 8
    radius = size // 4
    
    # 绘制一个圆角矩形作为背景
    draw.rounded_rectangle(
        [border, border, size-border, size-border],
        radius=radius,
        fill=(52, 152, 219, 255)  # 蓝色
    )
    
    # 在中心绘制一个简单的"A"字母
    font_size = size // 2
    text = "A"
    # 计算文本位置使其居中
    text_bbox = draw.textbbox((0, 0), text)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    # 绘制文本
    draw.text((x, y), text, fill=(255, 255, 255, 255))  # 白色
    
    return image

def main():
    # 确保输出目录存在
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 生成不同尺寸的图标
    sizes = [16, 48, 128]
    for size in sizes:
        icon = create_icon(size)
        output_path = os.path.join(output_dir, f'icon{size}.png')
        icon.save(output_path, 'PNG')
        print(f'Created icon: {output_path}')

if __name__ == '__main__':
    main() 