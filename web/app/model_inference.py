import torch
import os
import zipfile
from typing import Optional
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor
import re
import cv2
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


def _collapse_newlines_outside_code_fences(text: str) -> str:
    """把连续 3+ 换行压成 2 个（保留至多一空行），不改动 ``` 围栏内内容。"""
    parts = re.split(r"(```[\s\S]*?```)", text)
    out = []
    for part in parts:
        if part.startswith("```"):
            out.append(part)
        else:
            out.append(re.sub(r"\n{3,}", "\n\n", part))
    return "".join(out)


class LogicsParsingModel:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
        self.processor = None
        self._load_model()
    
    def _load_model(self):
        """加载模型和处理器，自动检测 GPU/CPU"""
        print(f"\n{'='*60}")
        print(f"正在加载模型: {self.model_path}")
        print(f"{'='*60}")
        
        # 检测硬件信息
        if torch.cuda.is_available():
            device_map = "cuda:0"
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            dtype = torch.bfloat16
            attn_impl = "sdpa"
            
            print(f"✅ 检测到 GPU:")
            print(f"   - 型号: {gpu_name}")
            print(f"   - 显存: {gpu_memory:.1f} GB")
            print(f"   - CUDA 版本: {torch.version.cuda}")
            print(f"   - 计算精度: bfloat16 (高效)")
            print(f"   - 注意力机制: sdpa (加速)")
        else:
            device_map = "cpu"
            dtype = torch.float32
            attn_impl = "eager"
            cpu_count = os.cpu_count()
            
            print(f"⚠️ 未检测到 GPU，使用 CPU:")
            print(f"   - CPU 核心数: {cpu_count}")
            print(f"   - 计算精度: float32 (标准)")
            print(f"   - 注意力机制: eager (兼容)")
            print(f"   - 提示: CPU 推理速度较慢，建议使用 GPU")
        
        print(f"{'='*60}\n")
        
        self.model = Qwen3VLForConditionalGeneration.from_pretrained(
            self.model_path,
            dtype=dtype,
            attn_implementation=attn_impl,
            device_map=device_map,
        )
        
        self.processor = AutoProcessor.from_pretrained(self.model_path)
        self.processor.image_processor.max_pixels = 7200 * 32 * 32
        self.processor.image_processor.min_pixels = 3136
        
        print(f"✅ 模型加载成功!\n")
    
    def inference(self, img_path: str, prompt: str = "QwenVL HTML"):
        """执行模型推理"""
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "image": img_path,
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt"
        )
        inputs = inputs.to(self.model.device)
        
        # 模型推理
        generated_ids = self.model.generate(
            **inputs, 
            max_new_tokens=16384, 
            temperature=0.1, 
            top_p=0.5, 
            repetition_penalty=1.05
        )
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = self.processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        
        # 确保返回字符串类型
        if not output_text or len(output_text) == 0:
            return ""
        result = output_text[0]
        # 如果结果是 None 或非字符串类型，转换为字符串
        if result is None:
            return ""
        if not isinstance(result, str):
            return str(result)
        return result
    
    def remove_lines_starting_with(self, text):
        lines = text.splitlines(keepends=True)
        filtered = []
        prefixes_to_remove = ('Z:')
        for line in lines:
            stripped = line.lstrip()
            if not stripped.strip():
                continue
            if stripped.startswith(prefixes_to_remove):
                continue
            filtered.append(line)  
        return "".join(filtered)

    def process_code_content(self, content: str) -> str:
        content = content.replace('```', '')
        content = re.sub(r'^\s*<pre[^>]*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'</pre>\s*$', '', content, flags=re.IGNORECASE)
        content = re.sub(r'^\s*<code[^>]*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'</code>\s*$', '', content, flags=re.IGNORECASE)
        return f"```code\n{content.strip()}\n```"

    def process_pseudocode_content(self, content: str) -> str:
        content = content.replace('```', '')
        content = re.sub(r'^\s*<(pre|code)[^>]*>', '', content, flags=re.IGNORECASE | re.MULTILINE)
        content = re.sub(r'</(pre|code)>\s*$', '', content, flags=re.IGNORECASE | re.MULTILINE)

        math_blocks = []
        def save_math(match):
            placeholder = f"___MATH_ID_{len(math_blocks)}___"
            math_blocks.append(match.group(0))
            return placeholder

        math_pattern = r'(\$\$.*?\$\$|\$.*?\$)'
        protected_content = re.sub(math_pattern, save_math, content, flags=re.DOTALL)
        protected_content = protected_content.replace(' ', '&nbsp;')
        protected_content = protected_content.replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')
        protected_content = protected_content.replace('\n', '<br>')

        final_content = protected_content
        for i, original_math in enumerate(math_blocks):
            placeholder = f"___MATH_ID_{i}___"
            final_content = final_content.replace(placeholder, original_math)

        return f"___\n<br>{final_content.strip()}<br>\n___"

    def qwenvl_cast_html_tag(self, input_text: str, image_output_mode: str = "base64", 
                              output_dir: Optional[str] = None, page_num: int = 0,
                              original_image_path: Optional[str] = None) -> str:
        """
        将 HTML 标签转换为 Markdown 格式。
        
        Args:
            input_text: AI 输出的原始文本
            image_output_mode: 图片输出模式 (base64/separate/none)
            output_dir: 输出目录（仅 separate 模式需要）
            page_num: 页码（用于生成唯一文件名）
            original_image_path: 原始页面图像路径（用于根据 data-bbox 裁剪）
            
        Returns:
            转换后的 Markdown 文本
        """
        # 确保 input_text 是字符串类型
        if input_text is None:
            input_text = ""
        if not isinstance(input_text, str):
            input_text = str(input_text)
        
        output = input_text
        
        # 调试：输出 AI 原始内容的前 2000 个字符
        if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
            print(f"\n{'='*80}")
            print(f"[调试] 页面 {page_num} - AI 原始输出预览（前 2000 字符）:")
            print(output[:2000])
            print(f"{'='*80}\n")
        
        # 调试：检查是否有 img 标签
        has_img_tags = '<img' in output.lower()
        has_data_bbox = 'data-bbox' in output.lower()
        if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
            print(f"\n{'='*60}")
            print(f"[调试] 页面 {page_num}:")
            print(f"  - 包含 <img> 标签: {has_img_tags}")
            print(f"  - 包含 data-bbox: {has_data_bbox}")
            print(f"  - 图片输出模式: {image_output_mode}")
            print(f"  - 输出目录: {output_dir}")
            
            if has_img_tags:
                # 提取所有 img 标签
                import re as re_module
                all_img_matches = re_module.findall(r'<img[^>]{0,500}>', output, re_module.IGNORECASE)
                print(f"  - 找到 {len(all_img_matches)} 个 img 标签")
                for i, match in enumerate(all_img_matches[:3]):  # 只打印前 3 个
                    print(f"  - img 标签 {i+1}: {match[:250]}...")
                    # 检查是否有 src 和 data-bbox
                    has_src = 'src=' in match.lower()
                    has_bbox = 'data-bbox' in match.lower()
                    print(f"    -> 有 src={has_src}, 有 data-bbox={has_bbox}")
            
            print(f"{'='*60}\n")
        
        # 用于保存单独的图片文件（separate 模式）
        extracted_images = []
        
        # 将带 data-bbox 的 img 标签转换为 Markdown 图片格式
        def convert_img_to_markdown(match):
            img_tag = match.group(0)
            if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                print(f"[转换] 正在处理 img 标签: {img_tag[:150]}...")
            
            # 提取 data-bbox 属性
            bbox_match = re.search(r'data-bbox=["\']?(\d+),(\d+),(\d+),(\d+)["\']?', img_tag, re.IGNORECASE)
            
            if not bbox_match:
                if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                    print(f"[警告] img 标签缺少 data-bbox 属性，跳过")
                return ''
            
            # 提取 src 属性（如果有）
            src_match = re.search(r'src=["\']([^"\']+)["\']', img_tag, re.IGNORECASE)
            alt_match = re.search(r'alt=["\']([^"\']*)["\']', img_tag, re.IGNORECASE)
            alt = alt_match.group(1) if alt_match else 'image'
            # 清理 alt 文本，移除可能导致 Markdown 解析问题的字符
            alt = alt.replace(')', '').replace('(', '').strip() or 'image'
            
            # 根据输出模式处理图片
            if image_output_mode == "none":
                if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                    print(f"[转换] 模式=none，跳过图片")
                return ''
            
            # 如果提供了原始图像路径，则从原图裁剪
            if original_image_path and os.path.exists(original_image_path):
                try:
                    from PIL import Image
                    import base64
                    from io import BytesIO
                    
                    # 解析 bbox 坐标（归一化坐标，范围 0-1000）
                    x1_norm, y1_norm, x2_norm, y2_norm = map(int, bbox_match.groups())
                    
                    # 打开原始图像
                    orig_img = Image.open(original_image_path)
                    img_width, img_height = orig_img.size
                    
                    # 转换为像素坐标
                    x1 = int(x1_norm / 1000 * img_width)
                    y1 = int(y1_norm / 1000 * img_height)
                    x2 = int(x2_norm / 1000 * img_width)
                    y2 = int(y2_norm / 1000 * img_height)
                    
                    # 确保坐标有效
                    x1, x2 = max(0, x1), min(img_width, x2)
                    y1, y2 = max(0, y1), min(img_height, y2)
                    
                    if x2 <= x1 or y2 <= y1:
                        if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                            print(f"[警告] 无效的 bbox 坐标: ({x1},{y1})-({x2},{y2})")
                        return ''
                    
                    # 裁剪图像
                    cropped_img = orig_img.crop((x1, y1, x2, y2))
                    if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                        print(f"[转换] 从原图裁剪: ({x1},{y1})-({x2},{y2}), 尺寸: {cropped_img.size}")
                    
                    if image_output_mode == "separate" and output_dir:
                        # 保存为独立文件
                        img_idx = len(extracted_images) + 1
                        img_filename = f"page_{page_num:03d}_img_{img_idx:03d}.png"
                        assets_dir = os.path.join(output_dir, "assets")
                        os.makedirs(assets_dir, exist_ok=True)
                        img_path = os.path.join(assets_dir, img_filename)
                        
                        # 转换为 RGB（如果需要）
                        if cropped_img.mode in ('RGBA', 'P'):
                            cropped_img = cropped_img.convert('RGB')
                        
                        cropped_img.save(img_path, 'PNG')
                        extracted_images.append(img_filename)
                        if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                            print(f"[转换] ✓ 图片已保存: {img_filename}")
                        return f'\n\n![{alt}](./assets/{img_filename})\n\n'
                    else:
                        # base64 模式：转为 base64
                        buffered = BytesIO()
                        if cropped_img.mode in ('RGBA', 'P'):
                            cropped_img = cropped_img.convert('RGB')
                        cropped_img.save(buffered, format='PNG')
                        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                        src = f"data:image/png;base64,{img_base64}"
                        if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                            print(f"[转换] base64 模式，长度: {len(src)} 字符")
                        # 使用 HTML img 标签以提高 Typora 等编辑器兼容性
                        return f'\n\n<img src="{src}" alt="{alt}" style="max-width: 100%; height: auto;" />\n\n'
                        
                except Exception as e:
                    if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                        print(f"[警告] 裁剪图像失败: {e}")
                        import traceback
                        traceback.print_exc()
                    # 降级：如果有 src 则使用 src，否则返回空
                    if src_match:
                        src = src_match.group(1)
                        # 降级时也使用 HTML img 标签以提高兼容性
                        return f'\n\n<img src="{src}" alt="{alt}" style="max-width: 100%; height: auto;" />\n\n'
                    return ''
            else:
                # 没有原始图像，尝试使用 src 中的 base64
                if src_match:
                    src = src_match.group(1)
                    if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                        print(f"[转换] 无原图，使用 src 中的数据")
                    
                    if image_output_mode == "separate" and output_dir and src.startswith('data:image/'):
                        # separate 模式：解码并保存
                        try:
                            import base64
                            header, base64_data = src.split(',', 1)
                            img_format = header.split('/')[1].split(';')[0]
                            img_bytes = base64.b64decode(base64_data)
                            img_idx = len(extracted_images) + 1
                            img_filename = f"page_{page_num:03d}_img_{img_idx:03d}.{img_format}"
                            assets_dir = os.path.join(output_dir, "assets")
                            os.makedirs(assets_dir, exist_ok=True)
                            img_path = os.path.join(assets_dir, img_filename)
                            
                            with open(img_path, 'wb') as f:
                                f.write(img_bytes)
                            
                            extracted_images.append(img_filename)
                            if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                                print(f"[转换] ✓ 图片已保存: {img_filename} ({len(img_bytes)} bytes)")
                            return f'\n\n![{alt}](./assets/{img_filename})\n\n'
                        except Exception as e:
                            if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                                print(f"[警告] 保存图片失败: {e}")
                            # 降级时使用 HTML img 标签以提高兼容性
                            return f'\n\n<img src="{src}" alt="{alt}" style="max-width: 100%; height: auto;" />\n\n'
                    else:
                        # base64 模式：直接使用
                        if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                            print(f"[转换] base64 模式，保持原样")
                        # 使用 HTML img 标签以提高 Typora 等编辑器兼容性
                        return f'\n\n<img src="{src}" alt="{alt}" style="max-width: 100%; height: auto;" />\n\n'
                else:
                    if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
                        print(f"[警告] 既无原图也无 src，跳过图片")
                    return ''
        
        # 修改正则：匹配所有 img 标签，不管有没有 data-bbox
        IMG_RE = re.compile(
            r'<img\b[^>]*\bdata-bbox\s*=\s*"?\d+,\d+,\d+,\d+"?[^>]*/?>',
            flags=re.IGNORECASE,
        )
        
        # 统计匹配数量
        matches_before = len(IMG_RE.findall(output))
        if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
            print(f"[调试] 正则匹配到 {matches_before} 个带 data-bbox 的 img 标签")
        
        output = IMG_RE.sub(convert_img_to_markdown, output)
        
        if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
            print(f"[调试] 转换完成，extracted_images 数量: {len(extracted_images)}")
            if extracted_images:
                print(f"[调试] 提取的图片文件: {extracted_images}")

        def replace_code(match):
            content = match.group(1)
            processed_content = self.process_code_content(content)
            return f"\n\n{processed_content}\n\n"
        
        code_pattern = re.compile(
            r'<div\b[^>]*class="code"[^>]*>(.*?)</div>',
            flags=re.DOTALL | re.IGNORECASE,
        )
        output = code_pattern.sub(replace_code, output)
        
        def replace_pseudocode(match):
            content = match.group(1)
            processed_content = self.process_pseudocode_content(content)
            return f"\n\n{processed_content}\n\n"
        
        pseudocode_pattern = re.compile(
            r'<div\b[^>]*class="pseudocode"[^>]*>(.*?)</div>',
            flags=re.DOTALL | re.IGNORECASE,
        )
        output = pseudocode_pattern.sub(replace_pseudocode, output)

        def strip_div(class_name: str, txt: str) -> str:
            if class_name in ['code', 'pseudocode']:
                return txt

            def replace_func(match):
                content = match.group(1)
                if class_name == 'chart':
                    content = re.sub(r'^\s*(click\s+|style\s+|linkStyle\s+|stroke|classDef\s+|class\s+)\b.*\n?', '', content, flags=re.MULTILINE | re.IGNORECASE)
                    content = re.sub(r'^\s*(?:%%|::icon).*\n?', '', content, flags=re.MULTILINE)
                    content = content.strip()
                    if content.startswith('mermaid'):
                        content = '```' + content
                    elif re.match(r'^```\s*mermaid', content):
                        pass
                    else:
                        content = '```mermaid\n' + content
                    if not content.endswith('```'):
                        content += '\n```'

                if class_name == 'music':
                    content = self.remove_lines_starting_with(content)
                    content = content.strip()
                    if content.startswith('abc'):
                        content = '```' + content
                    elif re.match(r'^```\s*abc', content):
                        pass
                    else:
                        content = '```abc\n' + content
                    if not content.endswith('```'):
                        content += '\n```'
                    
                return f"\n\n{content}\n\n"

            # chart/music 允许 class="foo chart bar"；其余与模型约定为整段 class 字符串（含空格）
            if class_name in ("chart", "music"):
                cls_attr = rf'class="[^"]*\b{re.escape(class_name)}\b[^"]*"'
            else:
                cls_attr = rf'class="{re.escape(class_name)}"'
            pattern = re.compile(
                rf'\s*<div\b[^>]*{cls_attr}[^>]*>(.*?)</div>\s*',
                flags=re.DOTALL | re.IGNORECASE,
            )
            return pattern.sub(replace_func, txt)

        # 须包含 chart：否则 <div class="chart"> 会原样留在 md 里，Typora 无法把其中 mermaid 当流程图渲染
        other_classes = [
            "chart",
            "music",
            "image",
            "chemistry",
            "table",
            "formula",
            "image caption",
            "table caption",
        ]
        for cls in other_classes:
            output = strip_div(cls, output)

        # 若仍有一层 div 仅包裹 ```mermaid 代码块，去掉 div，避免编辑器不把其识别为 fenced block
        output = re.sub(
            r'<div\b[^>]*>\s*(\n*\s*```mermaid\s*[\s\S]*?```)\s*</div>',
            r"\1",
            output,
            flags=re.IGNORECASE,
        )

        # 原先用 \n\n\1\n\n：相邻多个 <p> 会叠成 \n\n\n\n…，段落间空行过多
        def _replace_p(m):
            inner = m.group(1).strip()
            return "" if not inner else "\n" + inner + "\n"

        output = re.sub(
            r'<p\b[^>]*>(.*?)</p>',
            _replace_p,
            output,
            flags=re.DOTALL | re.IGNORECASE,
        )
        output = _collapse_newlines_outside_code_fences(output)

        output = output.replace(" </td>", "</td>")
        return output

    def plot_bbox(self, img_path: str, pred: str, output_path: str):
        img = cv2.imread(img_path)
        img_height, img_width, _ = img.shape
        bboxes = []
        pattern = re.compile(r'data-bbox="(\d+),(\d+),(\d+),(\d+)"')

        def replace_bbox(match):
            x1, y1, x2, y2 = map(int, match)
            x1 = int(x1/1000 * img_width)
            y1 = int(y1/1000 * img_height)
            x2 = int(x2/1000 * img_width)
            y2 = int(y2/1000 * img_height)
            bboxes.append([x1, y1, x2, y2])

        matches = re.findall(pattern, pred)
        if matches:
            for match in matches:
                replace_bbox(match)
        
        for bbox in bboxes:
            x1, y1, x2, y2 = bbox
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 8)

        cv2.imwrite(output_path, img)

    def _pdf_max_pages(self) -> int:
        try:
            from .settings_service import get_pdf_max_pages

            return get_pdf_max_pages()
        except Exception:
            return max(1, int(os.environ.get("PDF_MAX_PAGES", "80")))

    def _render_pdf_to_png_pages(self, pdf_path: str, pages_dir: str, max_pages: int):
        """返回 (每页 PNG 路径列表, PDF 原始总页数)。max_pages 为本任务最多渲染的页数。"""
        if fitz is None:
            raise RuntimeError("处理 PDF 需要安装 pymupdf：pip install pymupdf")
        os.makedirs(pages_dir, exist_ok=True)
        doc = fitz.open(pdf_path)
        try:
            n = len(doc)
            if n == 0:
                raise ValueError("PDF 无页面")
            cap = min(n, max(1, int(max_pages)))
            paths = []
            mat = fitz.Matrix(2.0, 2.0)
            for i in range(cap):
                page = doc.load_page(i)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                out = os.path.join(pages_dir, f"page_{i + 1:03d}.png")
                pix.save(out)
                paths.append(out)
        finally:
            doc.close()
        return paths, n

    def _remove_page_number_info(self, text: str) -> str:
        """清理 AI 输出中可能包含的页码信息和分页符。
        
        移除常见的页码标记格式：
        - Markdown 标题：## 第 X 页、### Page X 等
        - HTML 注释：<!-- 第 X 页 -->、<!-- Page X --> 等
        - 纯文本：第 X 页、Page X of Y 等（单独成行时）
        - Markdown 分页符：---、***、___ 等（单独成行时）
        """
        import re
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # 跳过单独的页码行和分页符
            if stripped:
                # Markdown 标题格式的页码
                if re.match(r'^#{1,6}\s*第\s*\d+\s*页\s*$', stripped):
                    continue
                if re.match(r'^#{1,6}\s*[Pp]age\s*\d+', stripped):
                    continue
                if re.match(r'^#{1,6}\s*页\s*\d+', stripped):
                    continue
                
                # HTML 注释格式的页码
                if re.match(r'^<!--\s*第\s*\d+\s*页\s*-->$', stripped):
                    continue
                if re.match(r'^<!--\s*[Pp]age\s*\d+.*-->$', stripped):
                    continue
                
                # 纯文本格式的页码（单独一行且内容很短）
                if (re.match(r'^第\s*\d+\s*页$', stripped) or 
                    re.match(r'^[Pp]age\s*\d+(\s*of\s*\d+)?$', stripped)) and len(stripped) < 30:
                    continue
                
                # Markdown 分页符（三个或更多连续的分隔符）
                # ---、***、___ 以及它们的变体
                if re.match(r'^-{3,}$', stripped):
                    continue
                if re.match(r'^\*{3,}$', stripped):
                    continue
                if re.match(r'^_{3,}$', stripped):
                    continue
            
            cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines)
        
        # 清理多余的空行（连续多个空行合并为一个）
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result

    def process_document(
        self,
        input_path: str,
        output_dir: str,
        job_id: str,
        progress_callback=None,
        prompt: str = "QwenVL HTML",
        cancel_event=None,
        max_pdf_pages: Optional[int] = None,
        show_page_numbers: bool = True,
        image_output_mode: str = "base64",
    ):
        """处理单张图片，或多页 PDF（逐页推理后合并 Markdown，可视化多页打包为 ZIP）。
        cancel_event 为可选 threading.Event：PDF 在页与页之间检查；单图仅在推理前检查。
        max_pdf_pages：PDF 时最多处理的页数；None 时使用系统全局上限。
        show_page_numbers：是否在输出中显示页码标记（如 <!-- 第 X 页 --> 和 ## 第 X 页）。
        image_output_mode：图片输出模式 (base64/separate/none)。"""
        try:
            ext = Path(input_path).suffix.lower()
            if ext == ".pdf":
                return self._process_pdf(
                    input_path,
                    output_dir,
                    job_id,
                    progress_callback,
                    prompt,
                    cancel_event,
                    max_pdf_pages,
                    show_page_numbers,
                    image_output_mode,
                )
            return self._process_single_image(
                input_path, output_dir, job_id, progress_callback, prompt, cancel_event, image_output_mode
            )
        except Exception as e:
            # 错误信息脱敏：记录详细日志，返回友好提示
            import logging
            logger = logging.getLogger("app")
            logger.exception(f"文档处理失败: {input_path}")
            
            error_msg = "文档处理失败，请联系管理员"
            if progress_callback:
                progress_callback(error_msg, -1)
            raise e

    def _process_single_image(
        self,
        img_path: str,
        output_dir: str,
        job_id: str,
        progress_callback,
        prompt: str,
        cancel_event=None,
        image_output_mode: str = "base64",
    ):
        if cancel_event is not None and cancel_event.is_set():
            raise ValueError("已停止：尚未生成任何内容")
        if progress_callback:
            progress_callback("正在加载图像...", 10)
        if progress_callback:
            progress_callback("正在执行模型推理...", 30)
        
        # 使用线程执行推理，以便支持停止
        import threading
        raw_output = [None]  # 用列表存储结果，以便在线程中修改
        inference_error = [None]
        
        def run_inference():
            try:
                raw_output[0] = self.inference(img_path, prompt)
            except Exception as e:
                inference_error[0] = e
        
        inference_thread = threading.Thread(target=run_inference, daemon=True)
        inference_thread.start()
        
        # 等待推理完成，同时检查是否被停止
        while inference_thread.is_alive():
            if cancel_event is not None and cancel_event.is_set():
                raise ValueError("已停止：推理过程中用户请求停止")
            inference_thread.join(timeout=0.5)  # 每 0.5 秒检查一次
        
        # 推理完成后检查结果
        if inference_error[0]:
            raise inference_error[0]
        
        if cancel_event is not None and cancel_event.is_set():
            raise ValueError("已停止：推理完成后用户请求停止")
        
        # 确保 raw_output 是字符串类型
        if raw_output[0] is None:
            raw_output[0] = ""
        if not isinstance(raw_output[0], str):
            raw_output[0] = str(raw_output[0])
        
        raw_output_str = raw_output[0]
        
        if progress_callback:
            progress_callback("正在处理输出格式...", 60)

        output_img_path = os.path.join(output_dir, f"{job_id}_vis.png")
        output_raw_path = os.path.join(output_dir, f"{job_id}_raw.mmd")
        output_mmd_path = os.path.join(output_dir, f"{job_id}.mmd")

        self.plot_bbox(img_path, raw_output_str, output_img_path)
        with open(output_raw_path, "w", encoding="utf-8") as f:
            f.write(raw_output_str)
        markdown_output = self.qwenvl_cast_html_tag(raw_output_str, image_output_mode, output_dir, page_num=1, original_image_path=img_path)
        with open(output_mmd_path, "w", encoding="utf-8") as f:
            f.write(markdown_output)

        # 检查是否有 assets 文件夹
        assets_dir = os.path.join(output_dir, "assets")
        has_assets = image_output_mode == "separate" and os.path.exists(assets_dir) and os.listdir(assets_dir)
        
        if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
            print(f"[调试] 图片输出模式: {image_output_mode}")
            print(f"[调试] assets 目录: {assets_dir}")
            print(f"[调试] assets 目录存在: {os.path.exists(assets_dir)}")
            if os.path.exists(assets_dir):
                print(f"[调试] assets 目录内容: {os.listdir(assets_dir)}")
            print(f"[调试] 是否生成 ZIP: {has_assets}")

        # 生成 ZIP 包供下载
        # - separate 模式：始终生成 ZIP（即使没有 assets，也打包其他文件）
        # - base64 模式：不生成 ZIP（图片已嵌入 .md 文件）
        download_zip_path = None
        if image_output_mode == "separate":
            download_zip_path = os.path.join(output_dir, f"{job_id}_result.zip")
            print(f"[调试] 生成完整结果 ZIP: {download_zip_path}")
            with zipfile.ZipFile(download_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # 添加 markdown 文件
                zf.write(output_mmd_path, arcname=f"{job_id}.mmd")
                
                # 添加 raw 文件
                zf.write(output_raw_path, arcname=f"{job_id}_raw.mmd")
                
                # 添加 visualization
                zf.write(output_img_path, arcname=f"{job_id}_vis.png")
                
                # 添加 assets 文件夹中的所有图片（如果存在）
                if os.path.exists(assets_dir) and os.path.isdir(assets_dir):
                    for img_file in os.listdir(assets_dir):
                        img_path_full = os.path.join(assets_dir, img_file)
                        if os.path.isfile(img_path_full):
                            zf.write(img_path_full, arcname=f"assets/{img_file}")
                            print(f"[调试] ZIP 中添加图片: assets/{img_file}")
            
            print(f"[调试] ZIP 生成完成")

        if progress_callback:
            progress_callback("处理完成！", 100)

        # 构建输出文件列表
        output_files = {
            "visualization": output_img_path,
            "raw": output_raw_path,
            "markdown": output_mmd_path,
        }
        # 仅 separate 模式提供 ZIP 下载
        if download_zip_path:
            output_files["download_zip"] = download_zip_path

        return {
            "raw_output": raw_output,
            "markdown_output": markdown_output,
            "output_files": output_files,
            "user_stopped": False,
            "partial": False,
            "pages_parsed": 1,
        }

    def _process_pdf(
        self,
        pdf_path: str,
        output_dir: str,
        job_id: str,
        progress_callback,
        prompt: str,
        cancel_event=None,
        max_pdf_pages: Optional[int] = None,
        show_page_numbers: bool = True,
        image_output_mode: str = "base64",
    ):
        pages_dir = os.path.join(output_dir, "pages")
        if cancel_event is not None and cancel_event.is_set():
            raise ValueError("已停止：尚未生成任何内容")
        if progress_callback:
            progress_callback("正在将 PDF 渲染为图像…", 8)
        cap = int(max_pdf_pages) if max_pdf_pages is not None else self._pdf_max_pages()
        page_paths, doc_page_count = self._render_pdf_to_png_pages(pdf_path, pages_dir, cap)
        total = len(page_paths)
        truncated_by_cap = doc_page_count > total

        vis_dir = os.path.join(output_dir, "vis")
        os.makedirs(vis_dir, exist_ok=True)

        raw_parts = []
        md_parts = []
        vis_files = []

        user_stopped = False
        for idx, page_img in enumerate(page_paths):
            if cancel_event is not None and cancel_event.is_set():
                user_stopped = True
                break
            pnum = idx + 1
            pct = 12 + int((idx + 1) / total * 78)
            if progress_callback:
                progress_callback(f"正在解析第 {pnum}/{total} 页…", min(pct, 90))

            raw_page = self.inference(page_img, prompt)
            
            # 确保 raw_page 是字符串类型
            if raw_page is None:
                raw_page = ""
            if not isinstance(raw_page, str):
                raw_page = str(raw_page)
            
            # 推理完成后检查是否被停止
            if cancel_event is not None and cancel_event.is_set():
                user_stopped = True
                break
            
            # 根据设置决定是否添加页码标记，以及是否清理 AI 输出中的页码信息
            if show_page_numbers:
                raw_parts.append(f"<!-- 第 {pnum} 页 -->\n{raw_page}")
                md_page = self.qwenvl_cast_html_tag(raw_page, image_output_mode, output_dir, pnum, original_image_path=page_img)
                md_parts.append(f"## 第 {pnum} 页\n\n{md_page}")
            else:
                # 清理 AI 输出中可能包含的页码信息
                cleaned_raw = self._remove_page_number_info(raw_page)
                raw_parts.append(cleaned_raw)
                md_page = self.qwenvl_cast_html_tag(cleaned_raw, image_output_mode, output_dir, pnum, original_image_path=page_img)
                md_parts.append(md_page)

            vis_path = os.path.join(vis_dir, f"page_{pnum:03d}.png")
            self.plot_bbox(page_img, raw_page, vis_path)
            vis_files.append(vis_path)

        if user_stopped and len(raw_parts) == 0:
            raise ValueError("已停止：尚未完成任何页面")

        if user_stopped and progress_callback:
            progress_callback("已停止，正在保存已生成页面…", 92)

        done_pages = len(raw_parts)
        combined_raw = "\n\n---\n\n".join(raw_parts)
        if truncated_by_cap:
            combined_raw = (
                f"<!-- 仅处理前 {total} 页（任务页数上限或 PDF 总页数） -->\n\n"
                + combined_raw
            )
        if user_stopped:
            combined_raw = (
                f"<!-- 用户中途停止，仅包含前 {done_pages} 页 -->\n\n" + combined_raw
            )
        combined_md = "\n\n---\n\n".join(md_parts)
        if show_page_numbers:
            if truncated_by_cap:
                combined_md = f"> 提示：仅解析前 {total} 页。\n\n---\n\n" + combined_md
            if user_stopped:
                combined_md = f"> 提示：已中途停止，仅包含前 {done_pages} 页。\n\n---\n\n" + combined_md

        output_raw_path = os.path.join(output_dir, f"{job_id}_raw.mmd")
        output_mmd_path = os.path.join(output_dir, f"{job_id}.mmd")
        with open(output_raw_path, "w", encoding="utf-8") as f:
            f.write(combined_raw)
        with open(output_mmd_path, "w", encoding="utf-8") as f:
            f.write(combined_md)

        # 如果是 separate 模式，检查是否有 assets 文件夹
        assets_dir = os.path.join(output_dir, "assets")
        has_assets = image_output_mode == "separate" and os.path.exists(assets_dir) and os.listdir(assets_dir)
        
        if os.environ.get("DEBUG_MODE", "").lower() in ("1", "true", "yes"):
            print(f"[调试] PDF-图片输出模式: {image_output_mode}")
            print(f"[调试] PDF-assets 目录: {assets_dir}")
            print(f"[调试] PDF-assets 目录存在: {os.path.exists(assets_dir)}")
            if os.path.exists(assets_dir):
                print(f"[调试] PDF-assets 目录内容: {os.listdir(assets_dir)}")
            print(f"[调试] PDF-是否生成 ZIP: {has_assets}")
        
        if done_pages == 1:
            single_vis = os.path.join(output_dir, f"{job_id}_vis.png")
            if vis_files:
                os.replace(vis_files[0], single_vis)
            vis_out = single_vis
        else:
            zip_path = os.path.join(output_dir, f"{job_id}_vis.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for p in vis_files:
                    zf.write(p, arcname=os.path.basename(p))
            vis_out = zip_path
        
        # 生成 ZIP 包供下载
        # - separate 模式：始终生成 ZIP（即使没有 assets，也打包其他文件）
        # - base64 模式：不生成 ZIP（图片已嵌入 .md 文件）
        download_zip_path = None
        if image_output_mode == "separate":
            download_zip_path = os.path.join(output_dir, f"{job_id}_result.zip")
            print(f"[调试] 生成完整结果 ZIP: {download_zip_path}")
            with zipfile.ZipFile(download_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # 添加 markdown 文件
                if os.path.exists(output_mmd_path):
                    zf.write(output_mmd_path, arcname=f"{job_id}.mmd")
                
                # 添加 raw 文件
                if os.path.exists(output_raw_path):
                    zf.write(output_raw_path, arcname=f"{job_id}_raw.mmd")
                
                # 添加可视化文件（单页 PNG 或多页 ZIP）
                if os.path.exists(vis_out):
                    zf.write(vis_out, arcname=os.path.basename(vis_out))
                
                # 添加 assets 文件夹中的所有图片（如果存在）
                if os.path.exists(assets_dir) and os.path.isdir(assets_dir):
                    for img_file in os.listdir(assets_dir):
                        img_path = os.path.join(assets_dir, img_file)
                        if os.path.isfile(img_path):
                            zf.write(img_path, arcname=f"assets/{img_file}")
                            print(f"[调试] ZIP 中添加图片: assets/{img_file}")
            
            print(f"[调试] ZIP 生成完成")

        if progress_callback:
            progress_callback("已停止，可下载已生成部分。" if user_stopped else "处理完成！", 100)

        partial = user_stopped and done_pages < total
        
        # 构建输出文件列表
        output_files = {
            "visualization": vis_out,
            "raw": output_raw_path,
            "markdown": output_mmd_path,
        }
        # 仅 separate 模式提供 ZIP 下载
        if download_zip_path:
            output_files["download_zip"] = download_zip_path
        
        return {
            "raw_output": combined_raw,
            "markdown_output": combined_md,
            "output_files": output_files,
            "user_stopped": user_stopped,
            "partial": partial,
            "pages_parsed": int(done_pages),
        }