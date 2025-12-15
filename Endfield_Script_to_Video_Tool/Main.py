import json
import os
from pathlib import Path
try:
    # Try new MoviePy 2.x import style
    from moviepy import ImageClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
except ImportError:
    # Fallback to old MoviePy 1.x import style  
    from moviepy.editor import ImageClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
import numpy as np
from PIL import Image

# 增加PIL图片大小限制
Image.MAX_IMAGE_PIXELS = None

# 设置参数
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30
FADE_DURATION = 0.5  # 淡入淡出时长
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

def apply_fade(clip, fade_in_duration, fade_out_duration):
    """应用淡入淡出效果"""
    def make_frame(t):
        frame = clip.get_frame(t)
        alpha = 1.0
        
        # 淡入
        if t < fade_in_duration:
            alpha = t / fade_in_duration
        # 淡出
        elif t > clip.duration - fade_out_duration:
            alpha = (clip.duration - t) / fade_out_duration
        
        return (frame * alpha).astype('uint8')
    
    return clip.transform(make_frame)

def create_text_clip(text, font_size, color='white', position='center', duration=1):
    """创建文本片段"""
    if not text:
        return None
    
    # 转换文本为字符串
    text = str(text)
    
    try:
        # 首先尝试使用系统字体
        fonts_to_try = ['SimHei', 'Microsoft-YaHei', 'Microsoft-YaHei-UI', 'SimSun', 'Arial-Unicode-MS']
        
        for font_name in fonts_to_try:
            try:
                txt_clip = TextClip(
                    text=text, 
                    font_size=font_size, 
                    color=color,
                    font=font_name,
                    size=(VIDEO_WIDTH - 200, None),
                    method='caption',
                    text_align='center'
                )
                txt_clip = txt_clip.with_position(position).with_duration(duration)
                return txt_clip
            except Exception:
                continue
        
        # 如果所有字体都失败，返回None
        print(f"  警告: 无法创建文本片段 '{text}'，跳过文本显示")
        return None
        
    except Exception as e:
        print(f"  警告: 无法创建文本片段 '{text}': {e}")
        return None

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
    
    # 加载背景图片
    try:
        bg_image = ImageClip(str(image_path))
        # 调整图片大小以适应16:9
        bg_image = bg_image.resized(height=VIDEO_HEIGHT)
        if bg_image.w < VIDEO_WIDTH:
            bg_image = bg_image.resized(width=VIDEO_WIDTH)
        # 居中裁剪
        bg_image = bg_image.cropped(
            x_center=bg_image.w/2, 
            y_center=bg_image.h/2,
            width=VIDEO_WIDTH, 
            height=VIDEO_HEIGHT
        )
    except Exception as e:
        print(f"加载图片失败: {e}")
        return False
    
    # 处理每个语音文件
    for voice_file in voice_files:
        voice_id = voice_file.stem  # 不含扩展名的文件名
        
        # 获取对应的文本
        title, desc = get_voice_text(character_data, voice_id)
        
        print(f"  处理: {voice_id}")
        print(f"    标题: {title}")
        print(f"    描述: {desc}")
        
        try:
            # 加载音频
            audio = AudioFileClip(str(voice_file))
            audio_duration = audio.duration
            
            # 计算这段视频的总时长（音频时长 + 间隔）
            segment_duration = audio_duration + INTERVAL_DURATION
            
            # 创建背景图片片段 - 使用音频时长，不包括间隔
            bg_clip = bg_image.with_duration(audio_duration)
            
            # 创建文本片段
            composite_clips = [bg_clip]
            
            # 添加标题（如果有）
            if title:
                title_clip = create_text_clip(
                    title, 
                    font_size=60, 
                    color='white',
                    position=('center', VIDEO_HEIGHT * 0.7),
                    duration=audio_duration
                )
                if title_clip:
                    composite_clips.append(title_clip)
            
            # 添加描述（如果有）
            if desc:
                desc_clip = create_text_clip(
                    desc, 
                    font_size=40, 
                    color='white',
                    position=('center', VIDEO_HEIGHT * 0.85),
                    duration=audio_duration
                )
                if desc_clip:
                    composite_clips.append(desc_clip)
            
            # 合成视频片段 - 只使用音频时长
            segment = CompositeVideoClip(composite_clips, size=(VIDEO_WIDTH, VIDEO_HEIGHT))
            segment = segment.with_audio(audio)
            segment = segment.with_duration(audio_duration)
            
            # 如果需要添加间隔，创建一个静音片段
            if INTERVAL_DURATION > 0:
                # 创建间隔片段（只有图片，没有音频）
                interval_clip = bg_image.with_duration(INTERVAL_DURATION)
                clips.append(segment)
                clips.append(interval_clip)
            else:
                clips.append(segment)
            
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
        preset='medium'
    )
    
    # 清理资源
    final_video.close()
    bg_image.close()
    
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
