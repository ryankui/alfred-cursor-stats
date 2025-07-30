#!/bin/bash

# Cursor Stats Alfred Workflow 打包脚本
# 使用方法: ./build.sh

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
WORKFLOW_NAME="Cursor-Stats"
OUTPUT_FILE="${WORKFLOW_NAME}.alfredworkflow"
REQUIRED_FILES=("cursor_stats.py" "info.plist" "icon.png")

echo -e "${BLUE}🚀 开始构建 Cursor Stats Alfred Workflow${NC}"
echo "----------------------------------------"

# 检查必需文件是否存在
echo -e "${YELLOW}📋 检查必需文件...${NC}"
for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo -e "${RED}❌ 错误: 缺少必需文件 $file${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ $file${NC}"
done

# 验证 plist 文件格式
echo -e "${YELLOW}🔍 验证 plist 文件格式...${NC}"
if command -v plutil >/dev/null 2>&1; then
    if plutil -lint info.plist >/dev/null 2>&1; then
        echo -e "${GREEN}✅ info.plist 格式正确${NC}"
    else
        echo -e "${RED}❌ 错误: info.plist 格式不正确${NC}"
        plutil -lint info.plist
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  警告: 未找到 plutil 命令，跳过 plist 验证${NC}"
fi

# 测试 Python 脚本
echo -e "${YELLOW}🐍 测试 Python 脚本...${NC}"
if python3 -m py_compile cursor_stats.py; then
    echo -e "${GREEN}✅ Python 脚本语法正确${NC}"
else
    echo -e "${RED}❌ 错误: Python 脚本语法错误${NC}"
    exit 1
fi

# 删除旧的打包文件
if [[ -f "$OUTPUT_FILE" ]]; then
    echo -e "${YELLOW}🗑️  删除旧的打包文件...${NC}"
    rm "$OUTPUT_FILE"
    echo -e "${GREEN}✅ 已删除 $OUTPUT_FILE${NC}"
fi

# 创建新的打包文件
echo -e "${YELLOW}📦 创建 Alfred workflow 包...${NC}"
zip -r "$OUTPUT_FILE" "${REQUIRED_FILES[@]}" -x "*.DS_Store*" "*.git*"

# 检查打包结果
if [[ -f "$OUTPUT_FILE" ]]; then
    file_size=$(ls -lh "$OUTPUT_FILE" | awk '{print $5}')
    echo -e "${GREEN}✅ 打包成功!${NC}"
    echo "📄 文件名: $OUTPUT_FILE"
    echo "📏 文件大小: $file_size"
    
    # 显示包内容
    echo -e "${BLUE}📋 包内容:${NC}"
    unzip -l "$OUTPUT_FILE"
    
    # 生成校验和
    if command -v shasum >/dev/null 2>&1; then
        echo -e "${BLUE}🔐 SHA256 校验和:${NC}"
        shasum -a 256 "$OUTPUT_FILE"
    fi
    
    echo ""
    echo -e "${GREEN}🎉 构建完成!${NC}"
    echo -e "${BLUE}💡 使用方法:${NC}"
    echo "   1. 双击 $OUTPUT_FILE 文件安装到 Alfred"
    echo "   2. 或者拖放到 Alfred Preferences > Workflows"
    echo ""
else
    echo -e "${RED}❌ 错误: 打包失败${NC}"
    exit 1
fi 