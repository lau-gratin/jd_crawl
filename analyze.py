import pandas as pd
import requests
import json
from collections import Counter
import numpy as np
from typing import List, Dict
from openai import OpenAI
from datetime import datetime
import os

class JDReviewAnalyzer:
    def __init__(self, api_key: str):
        """初始化分析器"""
        if not api_key:
            raise ValueError("必须提供有效的API密钥")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )

    def analyze_sentiment(self, text: str) -> Dict:
        """调用DeepSeek API分析评论情感"""
        try:
            payload = {
                "text": text,
                "task": "sentiment"
            }
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            return response.json()
        except Exception as e:
            print(f"情感分析API调用失败: {str(e)}")
            return {"sentiment": "neutral", "score": 0.5}

    def extract_aspects(self, text: str) -> Dict[str, Dict[str, str]]:
        """提取评论中的具体方面及其情感倾向"""
        try:
            prompt = f"""请分析以下评论，针对以下几个方面进行情感析：
            1. AI功能 (Ola friends AI助手的表现)
            2. 音质 (音质、音效相关)
            3. 外观 (包装、产品设计和美观度)

            评论内容：{text}
            
            请以JSON格式返回，格式如下：
            {{
                "ai_feature": {{"mentioned": true/false, "sentiment": "positive/negative/neutral", "comment": "具体评价"}},
                "sound_quality": {{"mentioned": true/false, "sentiment": "positive/negative/neutral", "comment": "具体评价"}},
                "appearance": {{"mentioned": true/false, "sentiment": "positive/negative/neutral", "comment": "具体评价"}}
            }}"""
            
            # 打印完整的请求信息
            print("发送到API的请求：", {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个专业的评论分析助手，请以JSON格式返回分析结果。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            })
            
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个专业的评论分析助手，请以JSON格式返回分析结果。"},
                    {"role": "user", "content": prompt}
                ],
                stream=False,
                temperature=0.7,
                max_tokens=1000
            )
            
            # 打印原始响应
            print("API原始响应：", response)
            
            content = response.choices[0].message.content.strip()
            
            # 去除 Markdown 代码块标记
            if content.startswith('```json'):
                content = content[7:]  # 移除开头的 ```json
            if content.endswith('```'):
                content = content[:-3]  # 移除结尾的 ```
            content = content.strip()  # 移除可能的多余空白
            
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError as je:
                print(f"JSON解析错误: {str(je)}")
                print(f"处理后的内容: {content}")
                # 返回默认结构
                return {
                    "ai_feature": {"mentioned": False, "sentiment": "neutral", "comment": ""},
                    "sound_quality": {"mentioned": False, "sentiment": "neutral", "comment": ""},
                    "appearance": {"mentioned": False, "sentiment": "neutral", "comment": ""}
                }
            
        except Exception as e:
            print(f"方面提取失败: {str(e)}")
            # 返回默认结构
            return {
                "ai_feature": {"mentioned": False, "sentiment": "neutral", "comment": ""},
                "sound_quality": {"mentioned": False, "sentiment": "neutral", "comment": ""},
                "appearance": {"mentioned": False, "sentiment": "neutral", "comment": ""}
            }

    def analyze_reviews(self, reviews_file: str, limit: int = 100) -> Dict:
        """分析评论并生成总结报告"""
        # 读取评论数据
        df = pd.read_csv(reviews_file, encoding='utf-8')
        if limit:
            df = df.head(limit)
        
        # 初始化统计数据
        aspect_stats = {
            'ai_feature': {'positive': 0, 'negative': 0, 'neutral': 0, 'mixed': 0, 'mentioned': 0},
            'sound_quality': {'positive': 0, 'negative': 0, 'neutral': 0, 'mixed': 0, 'mentioned': 0},
            'appearance': {'positive': 0, 'negative': 0, 'neutral': 0, 'mixed': 0, 'mentioned': 0}
        }
        
        regional_stats = {}  # 地域统计
        model_stats = {}    # 款式统计
        score_stats = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}  # 评分统计
        
        detailed_comments = {
            'ai_feature': [],
            'sound_quality': [],
            'appearance': []
        }
        
        # 创建详细分析结果DataFrame
        analysis_details = []
        
        for _, row in df.iterrows():
            review_text = row['评论内容']
            region = row.get('地区', '未知')
            model = row.get('商品款式', '标准版')
            score = row.get('评分', 5)
            
            # 分析评论
            aspects = self.extract_aspects(review_text)
            
            # 构建每条评论的分析结果
            analysis_row = {
                '评论内容': review_text,
                '地区': region,
                '商品款式': model,
                '评分': score,
                'AI功能_提及': aspects['ai_feature']['mentioned'],
                'AI功能_情感': aspects['ai_feature']['sentiment'],
                'AI功能_具体评价': aspects['ai_feature']['comment'],
                '音质_提及': aspects['sound_quality']['mentioned'],
                '音质_情感': aspects['sound_quality']['sentiment'],
                '音质_具体评价': aspects['sound_quality']['comment'],
                '外观_提及': aspects['appearance']['mentioned'],
                '外观_情感': aspects['appearance']['sentiment'],
                '外观_具体评价': aspects['appearance']['comment']
            }
            analysis_details.append(analysis_row)
            
            # 更新地域统计
            if region not in regional_stats:
                regional_stats[region] = {
                    'count': 0,
                    'ai_positive': 0,
                    'sound_positive': 0,
                    'appearance_positive': 0,
                    'avg_score': 0.0
                }
            regional_stats[region]['count'] += 1
            regional_stats[region]['avg_score'] += score
            
            # 更新款式统计
            if model not in model_stats:
                model_stats[model] = {
                    'count': 0,
                    'ai_positive': 0,
                    'sound_positive': 0,
                    'appearance_positive': 0,
                    'avg_score': 0.0
                }
            model_stats[model]['count'] += 1
            model_stats[model]['avg_score'] += score
            
            # 更新评分统计
            score_stats[score] += 1
            
            # 更新各方面统计
            for aspect, data in aspects.items():
                if data['mentioned']:
                    aspect_stats[aspect]['mentioned'] += 1
                    aspect_stats[aspect][data['sentiment']] += 1
                    if data['comment']:
                        detailed_comments[aspect].append({
                            'comment': data['comment'],
                            'region': region,
                            'model': model,
                            'score': score
                        })
                    
                    # 更新地域和款式的正面评价统计
                    if data['sentiment'] == 'positive':
                        if aspect == 'ai_feature':
                            regional_stats[region]['ai_positive'] += 1
                            model_stats[model]['ai_positive'] += 1
                        elif aspect == 'sound_quality':
                            regional_stats[region]['sound_positive'] += 1
                            model_stats[model]['sound_positive'] += 1
                        elif aspect == 'appearance':
                            regional_stats[region]['appearance_positive'] += 1
                            model_stats[model]['appearance_positive'] += 1
            
        # 计算地域和款式的平均分
        for region in regional_stats:
            regional_stats[region]['avg_score'] /= regional_stats[region]['count']
        for model in model_stats:
            model_stats[model]['avg_score'] /= model_stats[model]['count']
        
        # 创建详细分析Excel
        analysis_df = pd.DataFrame(analysis_details)
        output_file = reviews_file.replace('.csv', '_analysis.xlsx')
        analysis_df.to_excel(output_file, index=False)
        
        # 返回分析结果
        return {
            '总评论数': len(df),
            '各方面统计': aspect_stats,
            '地域统计': regional_stats,
            '款式统计': model_stats,
            '评分统计': score_stats,
            '详细评价': detailed_comments,
            '分析文件': output_file  # 添加输出文件路径到返回结果中
        }

    def generate_report(self, analysis_result: Dict) -> str:
        """生成分析报告"""
        total_reviews = analysis_result['总评论数']
        stats = analysis_result['各方面统计']
        regional_stats = analysis_result['地域统计']
        model_stats = analysis_result['款式统计']
        score_stats = analysis_result['评分统计']
        
        def get_sentiment_percentage(aspect: str, sentiment: str) -> str:
            if stats[aspect]['mentioned'] == 0:
                return "0%"
            return f"{(stats[aspect][sentiment] / stats[aspect]['mentioned'] * 100):.1f}%"
        
        report = f"""
京东商品评论分析报告
==================================================
分析样本: {total_reviews}条评论
分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

评分分布
------------------
• 总体评分: {sum([score * count for score, count in score_stats.items()]) / total_reviews:.1f}
• 评分分布:
  - 5星: {(score_stats[5] / total_reviews * 100):.1f}% ({score_stats[5]}条)
  - 4星: {(score_stats[4] / total_reviews * 100):.1f}% ({score_stats[4]}条)
  - 3星: {(score_stats[3] / total_reviews * 100):.1f}% ({score_stats[3]}条)
  - 2星: {(score_stats[2] / total_reviews * 100):.1f}% ({score_stats[2]}条)
  - 1星: {(score_stats[1] / total_reviews * 100):.1f}% ({score_stats[1]}条)

地域分析
------------------
"""
        # 添加地域分析
        sorted_regions = sorted(regional_stats.items(), 
                              key=lambda x: x[1]['count'], 
                              reverse=True)[:5]
        for region, data in sorted_regions:
            report += f"""
• {region}:
  - 评论数量: {data['count']}条 ({(data['count'] / total_reviews * 100):.1f}%)
  - 平均评分: {data['avg_score']:.1f}
  - AI功能好评率: {(data['ai_positive'] / data['count'] * 100):.1f}%
  - 音质好评率: {(data['sound_positive'] / data['count'] * 100):.1f}%
  - 外观好评率: {(data['appearance_positive'] / data['count'] * 100):.1f}%"""

        report += """

款式分析
------------------
"""
        # 添加款式分析
        sorted_models = sorted(model_stats.items(), 
                             key=lambda x: x[1]['count'], 
                             reverse=True)
        for model, data in sorted_models:
            report += f"""
• {model}:
  - 销量占比: {(data['count'] / total_reviews * 100):.1f}% ({data['count']}条)
  - 平均评分: {data['avg_score']:.1f}
  - AI功能好评率: {(data['ai_positive'] / data['count'] * 100):.1f}%
  - 音质好评率: {(data['sound_positive'] / data['count'] * 100):.1f}%
  - 外观好评率: {(data['appearance_positive'] / data['count'] * 100):.1f}%"""

        report += """

功能分析
------------------
"""
        # 添加原有的功能分析部分
        aspects = [
            ('AI功能', 'ai_feature'),
            ('音质体验', 'sound_quality'),
            ('外观设计', 'appearance')
        ]
        
        for aspect_name, aspect_key in aspects:
            report += f"""
{aspect_name}:
• 提及率: {(stats[aspect_key]['mentioned'] / total_reviews * 100):.1f}% ({stats[aspect_key]['mentioned']}/{total_reviews})
• 情感分布:
  - 正面评价: {get_sentiment_percentage(aspect_key, 'positive')} ({stats[aspect_key]['positive']}条)
  - 负面评价: {get_sentiment_percentage(aspect_key, 'negative')} ({stats[aspect_key]['negative']}条)
  - 中性评价: {get_sentiment_percentage(aspect_key, 'neutral')} ({stats[aspect_key]['neutral']}条)
  - 复杂评价: {get_sentiment_percentage(aspect_key, 'mixed')} ({stats[aspect_key]['mixed']}条)
• 典型评价:"""
            for comment_data in analysis_result['详细评价'][aspect_key][:3]:
                report += f"""
  * {comment_data['comment']} 
    (来自: {comment_data['region']}, 款式: {comment_data['model']}, 评分: {comment_data['score']})"""

        report += """

核心发现
------------------
"""
        # 添加一些数据分析见解
        report += self._generate_insights(analysis_result)
        
        return report

    def _generate_insights(self, analysis_result: Dict) -> str:
        """生成数据分析见解"""
        insights = []
        regional_stats = analysis_result['地域统计']
        model_stats = analysis_result['款式统计']
        
        # 找出最受欢迎的地区
        if regional_stats:  # 添加检查
            best_region = max(regional_stats.items(), 
                             key=lambda x: x[1]['avg_score'])
            insights.append(f"• {best_region[0]}地区的用户评价最高，平均评分达到{best_region[1]['avg_score']:.1f}分")
        
        # 找出最受欢迎的款式
        if model_stats:  # 添加检查
            best_model = max(model_stats.items(), 
                            key=lambda x: x[1]['avg_score'])
            insights.append(f"• {best_model[0]}是最受欢迎的款式，平均评分为{best_model[1]['avg_score']:.1f}分")
        
        # 分析功能特点
        stats = analysis_result['各方面统计']
        aspects = [
            ('AI功能', 'ai_feature'),
            ('音质', 'sound_quality'),
            ('外观', 'appearance')
        ]
        
        # 计算各方面的满意度
        satisfactions = {}
        for name, key in aspects:
            if stats[key]['mentioned'] > 0:
                satisfaction = (stats[key]['positive'] + stats[key]['mixed'] * 0.5) / stats[key]['mentioned'] * 100
                satisfactions[name] = satisfaction
        
        # 找出最强和弱的方面
        if satisfactions:  # 添加检查
            best_aspect = max(satisfactions.items(), key=lambda x: x[1])
            worst_aspect = min(satisfactions.items(), key=lambda x: x[1])
            
            insights.append(f"• 产品最强的方面是{best_aspect[0]}，满意度达到{best_aspect[1]:.1f}%")
            insights.append(f"• 最需要改进的方面是{worst_aspect[0]}，满意度为{worst_aspect[1]:.1f}%")
        else:
            insights.append("• 暂无足够的评论数据来分析产品特点")
        
        # 添加地域特征分析
        if regional_stats:  # 添加检查
            for region, data in regional_stats.items():
                if data['count'] >= analysis_result['总评论数'] * 0.1:  # 样本量达到10%以上的地区
                    features = []
                    if data['ai_positive'] / data['count'] > 0.7:
                        features.append("AI功能")
                    if data['sound_positive'] / data['count'] > 0.7:
                        features.append("音质")
                    if data['appearance_positive'] / data['count'] > 0.7:
                        features.append("外观")
                    
                    if features:
                        insights.append(f"• {region}的用户特别关注{'、'.join(features)}等特性")
        
        return "\n".join(insights) if insights else "暂无足够的数据生成分析见解"

def main():
    # 创建必要的目录
    os.makedirs("data/input", exist_ok=True)
    os.makedirs("data/output", exist_ok=True)
    
    # 从环境变量获取API密钥
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("请设置DEEPSEEK_API_KEY环境变量")
    
    analyzer = JDReviewAnalyzer(api_key)
    analysis_result = analyzer.analyze_reviews("data/input/jd_reviews.csv")
    report = analyzer.generate_report(analysis_result)
    
    # 添加时间戳到输出文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"data/output/analysis_report_{timestamp}.txt"
    
    # 保存报告
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n分析报告已保存至: {report_file}")
    print(f"详细分析结果已保存至: {analysis_result['分析文件']}")

if __name__ == "__main__":
    main()



