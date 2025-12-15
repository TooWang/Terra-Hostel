import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# 设置参数
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080

# 路径设置
BASE_DIR = Path(__file__).parent
CHARACTER_IMAGE_DIR = BASE_DIR / "CharacterImage"
CHARACTER_TABLE_PATH = BASE_DIR / "CharacterTable.json"
PREVIEW_DIR = BASE_DIR / "preview_frames"

# 增加PIL图片大小限制
Image.MAX_IMAGE_PIXELS = None

def load_character_data():
    """加载角色数据"""
    with open(CHARACTER_TABLE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def get_voice_text(character_data, voice_id):
    """根据语音ID获取对应的标题和描述"""
    # 尝试从profileVoice获取
    profile_voices = character_data.get('profileVoice', [])
    for voice in profile_voices:
        if voice.get('voId') == voice_id:
            title = voice.get('voiceTitle', {}).get('id', '')
            desc = voice.get('voiceDesc', {}).get('id', '')
            return title, desc
    
    # 如果profileVoice找不到，尝试voices
    voices = character_data.get('voices', [])
    for voice in voices:
        if voice.get('voId') == voice_id:
            title = voice.get('voiceTitle', {}).get('id', '')
            desc = voice.get('voiceDesc', {}).get('id', '')
            return title, desc
    
    return "", ""

def create_text_image(text, font_size, width, height, y_offset, x_offset=None, max_width=None):
    """使用PIL创建文本图像，支持自动换行"""
    if not text:
        return None
    
    # 转换为字符串
    text = str(text)
    
    # 创建透明背景
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 尝试加载中文字体
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", font_size)
        except:
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/simsun.ttc", font_size)
            except:
                font = ImageFont.load_default()
    
    # 确定最大宽度
    if max_width is None:
        max_width = width - (x_offset if x_offset else 0) - 40
    
    # 文本换行处理
    lines = []
    for paragraph in text.split('\n'):
        if not paragraph:
            lines.append('')
            continue
        
        current_line = ''
        for char in paragraph:
            test_line = current_line + char
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_width = bbox[2] - bbox[0]
            
            if line_width > max_width:
                if current_line:
                    lines.append(current_line)
                    current_line = char
                else:
                    lines.append(char)
            else:
                current_line = test_line
        
        if current_line:
            lines.append(current_line)
    
    # 计算总高度
    line_height = font_size + 10  # 行间距
    total_height = len(lines) * line_height
    
    # 计算起始y位置（以y_offset为第一行的中心）
    y = y_offset - (total_height // 2)
    
    # 计算x位置
    if x_offset is not None:
        x = x_offset
    else:
        x = 20
    
    # 确保不超出边界
    if x < 20:
        x = 20
    
    # 绘制每一行文本
    for line in lines:
        draw.text((x, y), line, font=font, fill=(0, 0, 0, 255))
        
        y += line_height
    
    return np.array(img)

def create_preview_frame(char_id, character_data):
    """为角色创建预览帧"""
    print(f"处理: {char_id}")
    
    # 获取角色文件夹和图片路径
    char_dir = BASE_DIR / char_id
    image_path = CHARACTER_IMAGE_DIR / f"{char_id}.jpg"
    
    if not char_dir.exists() or not image_path.exists():
        print(f"  跳过: 找不到文件夹或图片")
        return False
    
    # 获取第一个有文本的语音文件
    voice_files = sorted([f for f in char_dir.iterdir() if f.suffix == '.mp3'])
    
    title = ""
    desc = ""
    voice_name = ""
    
    for voice_file in voice_files:
        voice_id = voice_file.stem
        t, d = get_voice_text(character_data, voice_id)
        if t or d:  # 找到第一个有文本的
            title = t
            desc = d
            voice_name = voice_id
            break
    
    if not title and not desc:
        print(f"  跳过: 没有找到带文本的语音")
        return False
    
    print(f"  语音: {voice_name}")
    if title:
        print(f"  标题: {title}")
    if desc:
        print(f"  描述: {desc}")
    
    try:
        # 加载角色图片
        char_img = Image.open(str(image_path)).convert('RGB')
        
        # 角色图片宽度为总宽度的50%
        char_img_width = VIDEO_WIDTH // 2
        char_img_height = VIDEO_HEIGHT
        
        # 调整角色图片大小
        img_width, img_height = char_img.size
        aspect_ratio = img_width / img_height
        target_aspect = char_img_width / char_img_height
        
        if aspect_ratio > target_aspect:
            # 图片太宽
            new_height = char_img_height
            new_width = int(char_img_height * aspect_ratio)
            left = (new_width - char_img_width) // 2
            char_img = char_img.resize((new_width, new_height), Image.LANCZOS)
            char_img = char_img.crop((left, 0, left + char_img_width, new_height))
        else:
            # 图片太高
            new_width = char_img_width
            new_height = int(char_img_width / aspect_ratio)
            top = (new_height - char_img_height) // 2
            char_img = char_img.resize((new_width, new_height), Image.LANCZOS)
            char_img = char_img.crop((0, top, new_width, top + char_img_height))
        
        # 创建最终图像：左侧是角色图片，右侧是深灰色背景
        final_img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT), (30, 30, 30))
        final_img.paste(char_img, (0, 0))
        
        composite_img = np.array(final_img)
        
        # 文本显示在右侧，从宽度55%开始
        text_x_start = int(VIDEO_WIDTH * 0.55)
        
        # 添加标题
        if title:
            text_img = create_text_image(title, 80, VIDEO_WIDTH, VIDEO_HEIGHT, int(VIDEO_HEIGHT * 0.30), x_offset=text_x_start, max_width=400)
            if text_img is not None:
                alpha = text_img[:,:,3] / 255.0
                for c in range(3):
                    composite_img[:,:,c] = composite_img[:,:,c] * (1 - alpha) + text_img[:,:,c] * alpha
        
        # 添加描述 - 距离标题更近
        if desc:
            text_img = create_text_image(str(desc), 40, VIDEO_WIDTH, VIDEO_HEIGHT, int(VIDEO_HEIGHT * 0.48), x_offset=text_x_start, max_width=800)
            if text_img is not None:
                alpha = text_img[:,:,3] / 255.0
                for c in range(3):
                    composite_img[:,:,c] = composite_img[:,:,c] * (1 - alpha) + text_img[:,:,c] * alpha
        
        # 保存预览图
        output_img = Image.fromarray(composite_img.astype('uint8'))
        output_path = PREVIEW_DIR / f"{char_id}_preview.jpg"
        output_img.save(output_path, quality=95)
        
        print(f"  ✓ 已保存: {output_path.name}")
        return True
        
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("生成角色预览帧")
    print("=" * 60)
    
    # 创建预览输出目录
    PREVIEW_DIR.mkdir(exist_ok=True)
    print(f"\n输出目录: {PREVIEW_DIR}\n")
    
    # 加载角色数据
    all_data = load_character_data()
    
    # 获取所有角色ID
    character_ids = sorted([key for key in all_data.keys() if key.startswith('chr_')])
    print(f"找到 {len(character_ids)} 个角色\n")
    
    # 处理每个角色
    success_count = 0
    
    for i, char_id in enumerate(character_ids, 1):
        print(f"[{i}/{len(character_ids)}] ", end="")
        
        character_data = all_data[char_id]
        
        if create_preview_frame(char_id, character_data):
            success_count += 1
    
    # 输出统计信息
    print("\n" + "=" * 60)
    print(f"完成！成功生成 {success_count}/{len(character_ids)} 个预览图")
    print(f"预览图保存在: {PREVIEW_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    main()
