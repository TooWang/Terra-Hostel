import json
import os
from pathlib import Path
try:
    from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
except ImportError:
    from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# 增加PIL图片大小限制
Image.MAX_IMAGE_PIXELS = None

# 设置参数
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30
INTERVAL_DURATION = 1.0  # 文本之间的间隔

# 路径设置
BASE_DIR = Path(__file__).parent
CHARACTER_IMAGE_DIR = BASE_DIR / "CharacterImage"
CHARACTER_TABLE_PATH = BASE_DIR / "CharacterTable.json"

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

def create_text_image(text, font_size, width, height, y_offset, x_offset=None, max_width=None, font_name='simhei'):
    """使用PIL创建文本图像，支持自动换行和指定字体"""
    if not text:
        return None
    
    # 转换为字符串
    text = str(text)
    
    # 创建RGBA背景（透明）
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 尝试加载指定字体
    font = None
    
    if font_name.lower() == 'noto serif':
        try:
            font = ImageFont.truetype(os.path.join("Fonts", "NotoSerifSC-Bold.ttf"), font_size)
        except:
            try:
                font = ImageFont.truetype(os.path.join("Fonts", "NotoSerifSC-Bold.otf"), font_size)
            except:
                pass
    elif font_name.lower() == 'noto sans':
        try:
            font = ImageFont.truetype(os.path.join("Fonts", "NotoSansSC-Regular.ttf"), font_size)
        except:
            try:
                font = ImageFont.truetype(os.path.join("Fonts", "NotoSansSC-Regular.otf"), font_size)
            except:
                pass
    
    # 如果指定字体未找到，使用默认字体
    if font is None:
        try:
            font = ImageFont.truetype(os.path.join("Fonts", "NotoSerifSC-Bold.otf"), font_size)
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
    
    # 计算行高
    bbox = draw.textbbox((0, 0), "測", font=font)
    line_height = (bbox[3] - bbox[1]) + 10
    
    # 计算Y位置，以中心对齐
    total_height = len(lines) * line_height
    y = y_offset - (total_height // 2)
    
    # 计算x位置
    if x_offset is not None:
        x = x_offset
    else:
        x = 20
    
    # 确保不超出边界
    if x < 20:
        x = 20
    
    # 绘制每一行文本（黑色文本，不带阴影和描边）
    for line in lines:
        # 直接绘制黑色文本
        draw.text((x, y), line, font=font, fill=(0, 0, 0, 255))
        y += line_height
    
    return np.array(img)

def create_video_for_character(char_id, character_data):
    """为单个角色创建视频"""
    print(f"\n开始处理角色: {char_id}")
    
    # 获取角色文件夹和图片路径
    char_dir = BASE_DIR / char_id
    image_path = CHARACTER_IMAGE_DIR / f"{char_id}.jpg"
    
    if not char_dir.exists():
        print(f"找不到角色文件夹: {char_dir}")
        return False
    
    if not image_path.exists():
        print(f"找不到角色图片: {image_path}")
        return False
    
    # 获取所有语音文件
    voice_files = sorted([f for f in char_dir.iterdir() if f.suffix == '.mp3'])
    
    if not voice_files:
        print(f"没有找到语音文件")
        return False
    
    print(f"找到 {len(voice_files)} 个语音文件")
    
    # 创建视频片段列表
    clips = []
    
    # 加载背景和角色图片
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
        
        # 创建最终图像：使用Section_BG.png作为背景
        try:
            bg_path = BASE_DIR / "Section_BG.png"
            final_img = Image.open(bg_path).convert('RGB')
            final_img = final_img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS)
        except:
            # 如果加载失败，使用黑色背景
            print("  警告: 无法加载 Section_BG.png，使用黑色背景")
            final_img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
        
        # 将角色图片粘贴到左侧
        final_img.paste(char_img, (0, 0))
        
        bg_array = np.array(final_img)
        
    except Exception as e:
        print(f"加载图片失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 处理每个语音文件
    for voice_file in voice_files:
        voice_id = voice_file.stem
        
        # 获取对应的文本
        title, desc = get_voice_text(character_data, voice_id)
        
        if title or desc:  # 只显示有文本的语音
            print(f"  处理: {voice_id}")
            if title:
                print(f"    标题: {title}")
            if desc:
                print(f"    描述: {desc}")
        
        try:
            # 加载音频
            audio = AudioFileClip(str(voice_file))
            audio_duration = audio.duration
            
            # 创建包含文本的背景图像
            composite_img = bg_array.copy()
            
            # 文本显示在右侧，从宽度53%开始
            text_x_start = int(VIDEO_WIDTH * 0.53)
            
            # 添加标题（使用Noto Serif，字号80，位置在30%）
            if title:
                text_img = create_text_image(title, 80, VIDEO_WIDTH, VIDEO_HEIGHT, int(VIDEO_HEIGHT * 0.30), x_offset=text_x_start, max_width=800, font_name='noto serif')
                if text_img is not None:
                    # 合成图像（处理透明度）
                    alpha = text_img[:,:,3] / 255.0
                    for c in range(3):
                        composite_img[:,:,c] = composite_img[:,:,c] * (1 - alpha) + text_img[:,:,c] * alpha
            
            # 添加描述（使用Noto Sans，字号40，位置在55%）
            if desc:
                text_img = create_text_image(str(desc), 40, VIDEO_WIDTH, VIDEO_HEIGHT, int(VIDEO_HEIGHT * 0.55), x_offset=text_x_start, max_width=800, font_name='noto sans')
                if text_img is not None:
                    # 合成图像（处理透明度）
                    alpha = text_img[:,:,3] / 255.0
                    for c in range(3):
                        composite_img[:,:,c] = composite_img[:,:,c] * (1 - alpha) + text_img[:,:,c] * alpha
            
            # 创建视频片段
            video_clip = ImageClip(composite_img).with_duration(audio_duration)
            video_clip = video_clip.with_audio(audio)
            
            clips.append(video_clip)
            
            # 添加间隔
            if INTERVAL_DURATION > 0:
                interval_clip = ImageClip(bg_array).with_duration(INTERVAL_DURATION)
                clips.append(interval_clip)
            
        except Exception as e:
            print(f"  处理语音文件失败: {voice_file}, 错误: {e}")
            continue
    
    if not clips:
        print("没有成功创建任何视频片段")
        return False
    
    # 合并所有片段
    print(f"合并 {len(clips)} 个视频片段...")
    final_video = concatenate_videoclips(clips, method="compose")
    
    # 输出视频
    output_dir = char_dir / "output_videos"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{char_id}_complete.mp4"
    
    print(f"正在导出视频: {output_path}")
    final_video.write_videofile(
        str(output_path),
        fps=FPS,
        codec='libx264',
        audio_codec='aac',
        preset='medium',
        threads=4
    )
    
    # 清理资源
    final_video.close()
    for clip in clips:
        clip.close()
    
    print(f"✓ 视频创建成功: {output_path}")
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("开始批量生成角色语音视频")
    print("=" * 60)
    
    # 加载角色数据
    print("\n加载角色数据...")
    all_data = load_character_data()
    
    # 获取所有角色ID
    character_ids = [key for key in all_data.keys() if key.startswith('chr_')]
    print(f"找到 {len(character_ids)} 个角色")
    
    # 处理每个角色
    success_count = 0
    failed_count = 0
    
    for i, char_id in enumerate(character_ids, 1):
        print(f"\n[{i}/{len(character_ids)}] 处理角色: {char_id}")
        
        character_data = all_data[char_id]
        
        try:
            if create_video_for_character(char_id, character_data):
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"处理角色 {char_id} 时发生错误: {e}")
            import traceback
            traceback.print_exc()
            failed_count += 1
    
    # 输出统计信息
    print("\n" + "=" * 60)
    print("处理完成！")
    print(f"成功: {success_count} 个")
    print(f"失败: {failed_count} 个")
    print("=" * 60)

if __name__ == "__main__":
    main()
