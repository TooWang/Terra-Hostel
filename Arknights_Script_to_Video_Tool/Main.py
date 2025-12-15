#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from pathlib import Path

from moviepy import *
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import subprocess
import time


class CharacterVideoMaker:
    def __init__(self,
                 char_image_path,
                 audio_folder,
                 json_path,
                 background_path,
                 cv_name="配音演员姓名",
                 audio_interval=3,
                 output_resolution=(1920, 1080)):
        """
        初始化视频制作器

        Args:
            char_image_path: 人物图片路径
            audio_folder: 音频文件夹路径
            json_path: charword_table.json文件路径
            background_path: 背景图路径
            cv_name: 配音演员姓名
            audio_interval: 音频间隔时间（秒）
            output_resolution: 输出分辨率
        """
        self.char_image_path = char_image_path
        self.audio_folder = audio_folder
        self.json_path = json_path
        self.background_path = background_path
        self.cv_name = cv_name
        self.audio_interval = audio_interval
        self.width, self.height = output_resolution

        # 从人物图片名提取ID
        self.char_name = Path(char_image_path).stem
        self.char_id = self.char_name

        # 加载JSON数据
        with open(json_path, 'r', encoding='utf-8') as f:
            json_full = json.load(f)
            self.json_data = json_full.get('charWords', json_full)

        # 预处理背景图（只处理一次）
        self.processed_bg = self._preprocess_background()

        # 预处理人物图片（只处理一次）
        self.processed_char = self._preprocess_character()

    def _preprocess_background(self):
        """预处理背景图：调整大小并添加模糊效果"""
        print("预处理背景图...")
        bg = Image.open(self.background_path).convert('RGBA')

        # 调整到目标分辨率
        bg = bg.resize((self.width, self.height), Image.Resampling.LANCZOS)

        # 应用高斯模糊
        bg = bg.filter(ImageFilter.GaussianBlur(radius=10))

        return np.array(bg)

    def _preprocess_character(self):
        """预处理人物图片：调整大小"""
        print("预处理人物图片...")
        char_img = Image.open(self.char_image_path).convert('RGBA')

        # 计算目标高度（占屏幕70%）
        target_height = int(self.height * 0.7)
        aspect_ratio = char_img.width / char_img.height
        target_width = int(target_height * aspect_ratio)

        # 调整大小
        char_img = char_img.resize((target_width, target_height), Image.Resampling.LANCZOS)

        return char_img, (target_width, target_height)

    def create_frame_with_text(self, title, voice_text, x, y):
        """
        创建单帧完整图像（背景+人物+所有文字）
        这是性能优化的关键：一次性渲染所有元素
        """
        # 复制背景（已经是模糊的）
        frame = Image.fromarray(self.processed_bg.copy())

        # 获取字体
        font_cv, font_title, font_text, font_name, font_ENname = self._get_fonts()

        text_color = (255, 255, 255, 255)

        '''
        # 黑色半透明背景（50%透明度）
        bg_color = (0, 0, 0, 128)  # 黑色，50%透明

        # 1. 人物图片位置（左侧，完全无背景框）
        char_img, (char_w, char_h) = self.processed_char
        char_x = 30  # 人物图片左边距
        char_y = (self.height - char_h) // 2  # 垂直居中
        char_bottom = char_y + char_h  # 人物下缘位置

        # 先粘贴人物图片（无任何背景）
        frame.paste(char_img, (char_x, char_y), char_img)

        # 创建半透明层仅用于文字背景
        overlay = Image.new('RGBA', frame.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        

        # 2. CV信息位置（右上角）
        cv_text = f"CV: {self.cv_name}"
        cv_box_height = 65  # CV背景框高度
        cv_x = self.width - 350  # 距离右边350像素
        cv_y = 50  # 背景框顶部位置
        cv_bg_rect = (cv_x - 10, cv_y, cv_x + 300, cv_y + cv_box_height)
        overlay_draw.rounded_rectangle(cv_bg_rect, radius=5, fill=bg_color)
        '''

        formation = Image.open(background_path)
        formation = formation.convert("RGBA")
        formation = formation.resize(size=(1920, 1080))
        formation = formation.filter(ImageFilter.GaussianBlur(10))
        formation = ImageEnhance.Brightness(formation).enhance(0.5)
        formation = ImageEnhance.Color(formation).enhance(0.8)
        rm_image = Image.open("Cover.png")
        rm_image = rm_image.convert("RGBA")
        Tachie = Image.open(char_image_path)
        Tachie = Tachie.convert("RGBA")

        TachieMask = Image.open("Mask.png")
        TachieMask = TachieMask.convert("RGBA")

        TachieWidth, TachieHeight = Tachie.size
        maskImg = Image.new("L", (TachieWidth, TachieHeight))
        maskDraw = ImageDraw.Draw(maskImg)
        maskDraw.rectangle([(TachieWidth / 1.4), 0, TachieWidth, TachieHeight], fill=255)
        maskImg = maskImg.filter(ImageFilter.GaussianBlur(80))

        Empty = Image.new("RGBA", (TachieWidth, TachieHeight))
        maskDraw = ImageDraw.Draw(Empty)

        formation.alpha_composite(rm_image)
        formation.alpha_composite(Image.composite(Empty, Tachie, maskImg), ((-round(TachieWidth / 2) + 520) + x, 90 - y))

        # 3. 计算文本区域
        content_width = 800

        # 绘制所有文本
        final_draw = ImageDraw.Draw(formation)


        # CV文本（垂直居中，补偿Bold字体偏移）
        # 使用临时画布测量文本实际高度
        temp_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_img)
        '''
        cv_bbox = temp_draw.textbbox((0, 0), cv_text, font=font_cv)
        cv_text_height = cv_bbox[3] - cv_bbox[1]
        # 在背景框内垂直居中，减去偏移量补偿Bold字体
        baseline_offset = 5  # Bold字体补偿
        cv_text_y = cv_y + (cv_box_height - cv_text_height) // 2 - baseline_offset
        final_draw.text((cv_x, cv_text_y), cv_text, font=font_cv, fill=text_color)
        '''

        final_draw.text((834, 100), Char_CN_Name, font=font_name, fill=text_color)
        width = font_name.getlength(text=Char_CN_Name) + 835
        print(type(width))
        accentCN, descentCN = font_name.getmetrics()
        ascentEN, descentEN = font_ENname.getmetrics()
        height = 112 + accentCN - ascentEN
        '''
        print(height, ascentEN, descentEN, accentCN)
        '''
        final_draw.text((width, height), Char_EN_Name, font=font_ENname, fill=text_color)

        # 标题文本（水平和垂直居中，补偿Bold字体偏移）
        final_draw.text((912, 321), title, font=font_title, fill=text_color)

        # 正文文本（左对齐，垂直居中）
        # 先进行文本换行
        max_width = 800
        lines = self._wrap_text(voice_text, font_text, max_width, temp_draw)

        # 计算所有行的总高度
        line_height = 60  # 行高（适应36号字体）
        total_text_height = len(lines) * line_height

        text_area_top = 480

        # 垂直居中起始位置
        text_start_y = text_area_top + (400 - total_text_height) // 2

        # 绘制每行文本（左对齐）
        text_x = 912
        for i, line in enumerate(lines):
            line_y = text_start_y + i * line_height
            final_draw.text((text_x, line_y), line, font=font_text, fill=text_color)
        '''
        formation.show()
        '''

        return np.array(formation)

    def _get_fonts(self):
        """获取字体对象"""
        try:
            # 使用本地Fonts文件夹的MiSans字体
            font_dir = "Fonts"

            # 尝试加载MiSans字体
            font_cv = font_title = font_text = None

            font_name = [
                os.path.join(font_dir, "NotoSerifSC-Bold.ttf")
            ]
            for font_path in font_name:
                if os.path.exists(font_path):
                    font_name = ImageFont.truetype(font_path, size=160)

            font_ENname = [
                os.path.join(font_dir, "NotoSansSC-Regular.ttf")
            ]
            for font_path in font_ENname:
                if os.path.exists(font_path):
                    font_ENname = ImageFont.truetype(font_path, size=72)

            # CV字体使用Semibold
            cv_font_paths = [
                os.path.join(font_dir, "NotoSansSC-Regular.ttf"),
            ]
            for font_path in cv_font_paths:
                if os.path.exists(font_path):
                    font_cv = ImageFont.truetype(font_path, 36)
                    break

            # 标题使用Bold或Demibold（粗体）
            title_font_paths = [
                os.path.join(font_dir, "NotoSansSC-Medium.ttf")
            ]
            for font_path in title_font_paths:
                if os.path.exists(font_path):
                    font_title = ImageFont.truetype(font_path, 60)
                    break

            # 正文使用Regular或Semibold（较细）
            text_font_paths = [
                os.path.join(font_dir, "NotoSansSC-Regular.ttf")
            ]
            for font_path in text_font_paths:
                if os.path.exists(font_path):
                    font_text = ImageFont.truetype(font_path, 36)  # 字体大小调整为50
                    break

            # 如果MiSans字体未找到，使用备用字体
            if not font_cv or not font_title or not font_text:
                print("警告：未找到完整的字体，使用备用字体")
                fallback_paths = [
                    "C:/Windows/Fonts/msyh.ttc",
                    "C:/Windows/Fonts/simhei.ttf",
                ]
                for font_path in fallback_paths:
                    if os.path.exists(font_path):
                        if not font_cv:
                            font_cv = ImageFont.truetype(font_path, 36)
                        if not font_title:
                            font_title = ImageFont.truetype(font_path, 60)
                        if not font_text:
                            font_text = ImageFont.truetype(font_path, 50)
                        if not font_name:
                            font_name = ImageFont.truetype(font_path, 160)
                        if not font_ENname:
                            font_ENname = ImageFont.truetype(font_path, 72)
                        break

            # 最后的后备方案
            if not font_cv:
                font_cv = ImageFont.load_default()
            if not font_title:
                font_title = ImageFont.load_default()
            if not font_text:
                font_text = ImageFont.load_default()
            if not font_name:
                font_name = ImageFont.load_default()

        except Exception as e:
            print(f"字体加载警告: {e}")
            default = ImageFont.load_default()
            font_cv = font_title = font_text = default

        return font_cv, font_title, font_text, font_name, font_ENname

    def _wrap_text(self, text, font, max_width, draw):
        """文本自动换行"""
        lines = []
        current_line = ""

        for char in text:
            if char == '\n':
                if current_line:
                    lines.append(current_line)
                    current_line = ""
            else:
                test_line = current_line + char
                # 测试文本宽度
                bbox = draw.textbbox((0, 0), test_line, font=font)
                line_width = bbox[2] - bbox[0]

                if line_width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = char

        if current_line:
            lines.append(current_line)

        return lines

    def process_single_audio(self, audio_file, voice_data, x, y):
        """
        处理单个音频文件（优化版）
        """
        # 加载音频
        audio = AudioFileClip(audio_file)
        duration = audio.duration + self.audio_interval  # 包含间隔时间

        # 获取文本信息
        title_text = voice_data.get('voiceTitle', '未知标题')
        voice_text = voice_data.get('voiceText', '')
        print(title_text, voice_text)

        # 创建单帧图像
        frame_array = self.create_frame_with_text(title_text, voice_text, x, y)

        # 创建视频片段（使用单帧图像）
        video = ImageClip(frame_array, duration=duration)
        VideoName = title_text + ".mp4"
        video.write_videofile(filename=VideoName, fps= 24 , temp_audiofile_path="./Temp", threads=4)

        EffectedVideo = VideoFileClip(VideoName)
        EffectedVideo.with_effects([vfx.CrossFadeIn(1), vfx.CrossFadeOut(1)]).copy()

        '''
        VideoName = VideoFileClip("./Temp/"+VideoName)
        VideoName.preview()
        '''


        # 添加音频（音频结束后保持画面）
        EffectedVideo = video.with_audio(audio)

        return EffectedVideo

    def find_voice_data(self, voice_id):
        """根据voiceId查找语音数据"""
        full_voice_id = f"CN_{voice_id}" if not voice_id.startswith('CN_') else voice_id

        # 尝试不同的key格式
        possible_keys = [
            f"{self.char_id}_{full_voice_id}",
            f"{self.char_id}_CN_{voice_id}",
        ]

        # 查找匹配的数据
        if isinstance(self.json_data, dict):
            for key in possible_keys:
                if key in self.json_data:
                    return self.json_data[key]

            # 遍历所有值查找匹配
            for key, item in self.json_data.items():
                if isinstance(item, dict):
                    if (item.get('charId') == self.char_id and
                            item.get('voiceId') == full_voice_id):
                        return item

        return None

    def create_video(self, x, y):
        """创建完整视频（优化版）"""
        # 获取所有音频文件
        audio_files = sorted([
            f for f in Path(self.audio_folder).glob('CN_*.wav')
        ])

        if not audio_files:
            print("未找到音频文件")
            return

        video_clips = []
        total_files = len(audio_files)

        print(f"\n找到 {total_files} 个音频文件")
        print("-" * 40)

        for idx, audio_file in enumerate(audio_files, 1):
            # 提取音频ID
            audio_name = audio_file.stem
            voice_id = audio_name.split('_')[1] if '_' in audio_name else audio_name

            # 查找对应的语音数据
            voice_data = self.find_voice_data(voice_id)

            if not voice_data:
                print(f"[{idx}/{total_files}] 跳过 {audio_name} (未找到文本数据)")
                continue

            print(f"[{idx}/{total_files}] 处理: {audio_name}")
            print(f"  标题: {voice_data.get('voiceTitle', '未知')}")

            # 处理单个音频
            clip = self.process_single_audio(str(audio_file), voice_data, x, y)
            video_clips.append(clip)

        # 合并所有视频片段
        if video_clips:
            print("\n合并视频片段...")
            final_video = concatenate_videoclips(video_clips)

            # 输出文件名
            output_filename = f"{self.char_name}.mp4"

            # 导出视频
            print(f"导出视频: {output_filename}")
            print("-" * 40)
            self.export_video_optimized(final_video, output_filename)
        else:
            print("没有可用的视频片段")

    def export_video_optimized(self, final_video, output_filename):
        """优化的视频导出方法"""
        start_time = time.time()

        # 检查是否有GPU支持
        gpu_available = self.check_gpu_support()

        if gpu_available:
            print("使用 GPU 加速导出...")
            # GPU加速导出
            final_video.write_videofile(
                output_filename,
                fps=24,
                codec='h264_nvenc',  # NVIDIA GPU编码
                preset='fast',
                bitrate="8000k",
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                logger='bar'
            )
        else:
            print("使用 CPU 导出（优化参数）...")
            # CPU导出（优化参数）
            final_video.write_videofile(
                output_filename,
                fps=24,
                codec='libx264',
                preset='faster',  # 平衡速度和质量
                bitrate="6000k",
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                logger='bar',
                threads=8  # 多线程
            )

        elapsed_time = time.time() - start_time
        file_size = os.path.getsize(output_filename) / (1024 * 1024)

        print(f"\n✓ 导出完成!")
        print(f"  用时: {elapsed_time:.2f} 秒")
        print(f"  文件: {output_filename}")
        print(f"  大小: {file_size:.2f} MB")

    def check_gpu_support(self):
        """检查GPU编码支持"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-hide_banner', '-encoders'],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            return 'h264_nvenc' in result.stdout
        except:
            return False

    def Tachie_Check(self):
        formation = Image.open(background_path)
        formation = formation.resize(size=(1920, 1080))
        formation = formation.convert("RGBA")
        formation = formation.filter(ImageFilter.GaussianBlur(10)); formation = ImageEnhance.Brightness(formation).enhance(0.5); formation = ImageEnhance.Color(formation).enhance(0.8)
        rm_image = Image.open("Cover.png")
        rm_image = rm_image.convert("RGBA")
        Tachie = Image.open(char_image_path)
        Tachie = Tachie.convert("RGBA")
        TachieRuler = Image.open("TachieRuler.png")
        TachieRuler = TachieRuler.convert("RGBA")

        TachieMask = Image.open("Mask.png")
        TachieMask = TachieMask.convert("RGBA")

        TachieWidth, TachieHeight = Tachie.size
        maskImg = Image.new("L", (TachieWidth, TachieHeight))
        maskDraw = ImageDraw.Draw(maskImg)
        maskDraw.rectangle([(TachieWidth / 1.4), 0, TachieWidth, TachieHeight], fill=255)
        maskImg = maskImg.filter(ImageFilter.GaussianBlur(80))

        Empty = Image.new("RGBA", (TachieWidth, TachieHeight))
        maskDraw = ImageDraw.Draw(Empty)

        OriginalX, OriginalY = (-round(TachieWidth / 2) + 520), 90
        x, y = 0, 0

        while True:
            formation.alpha_composite(rm_image)
            formation.alpha_composite(Image.composite(Empty, Tachie, maskImg), (OriginalX + x, OriginalY - y))
            formation.alpha_composite(TachieRuler)
            formation.show()

            check =input("立繪位置是否合適（Y/N）或R重新打開預覽圖:")

            if check == "N":
                x, y = map(int, input("請輸入微調量（x y）:").split())
                formation = Image.open(background_path)
                formation = formation.resize(size=(1920, 1080))
                formation = formation.convert("RGBA")
                formation = formation.filter(ImageFilter.GaussianBlur(10)); formation = ImageEnhance.Brightness(formation).enhance(0.5); formation = ImageEnhance.Color(formation).enhance(0.8)
            elif check == "R":
                formation.show()
            elif check == "Y":
                break

        return(x, y)

# ========== 配置参数 =========
# 请根据实际情况修改以下路径和参数
Char_CN_Name = "遙"
Char_EN_Name = "Haruka"
char_image_path = "char_4202_haruka.png"  # 人物图片路径
audio_folder = "Haruka_voice"  # 音频文件夹路径
json_path = "charword_table.json"  # JSON文件路径
background_path = "background.png"  # 背景图路径
cv_name = "丰田萌绘"  # 配音演员姓名
audio_interval = 3  # 音频间隔（秒）

def main():
    """主函数"""


    # ========== 运行程序 ==========
    print("\n" + "=" * 60)
    print("角色语音视频制作工具 v2.0 (优化版)")
    print("=" * 60)

    # 检查文件是否存在
    files_to_check = [
        ("人物图片", char_image_path),
        ("音频文件夹", audio_folder),
        ("JSON文件", json_path),
        ("背景图", background_path)
    ]

    all_exist = True
    for name, path in files_to_check:
        if os.path.exists(path):
            print(f"✓ {name}: {path}")
        else:
            print(f"✗ {name}: {path} (不存在)")
            all_exist = False

    if not all_exist:
        print("\n请检查文件路径后重试")
        return

    print("\n开始制作视频...")
    print("-" * 40)

    try:
        # 创建视频制作器
        maker = CharacterVideoMaker(
            char_image_path=char_image_path,
            audio_folder=audio_folder,
            json_path=json_path,
            background_path=background_path,
            cv_name=cv_name,
            audio_interval=audio_interval
        )

        x, y = maker.Tachie_Check()

        # 开始制作
        maker.create_video(x, y)

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()