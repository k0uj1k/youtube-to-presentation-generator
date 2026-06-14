#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Iフレーム抽出高速化のベンチマークスクリプト

使用方法:
  python benchmark_iframe_extraction.py "YouTube動画URL"

例:
  python benchmark_iframe_extraction.py "https://www.youtube.com/watch?v=QqArUuwDpxU"
"""

import sys
import time
import os

# パスの設定
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from app.services.youtube_service import process_youtube_to_presentation


def benchmark_video_processing(url: str, change_levels: list = None):
    """
    異なる変化レベルで同じ動画を処理し、パフォーマンスを測定する。
    
    Parameters
    ----------
    url : str
        YouTube動画のURL
    change_levels : list
        テストする変化レベルのリスト（デフォルト: [3, 5, 7]）
    """
    if change_levels is None:
        change_levels = [3, 5, 7]
    
    print("=" * 70)
    print("YouTube Iフレーム抽出 - ベンチマークテスト")
    print("=" * 70)
    print(f"テストURL: {url}")
    print(f"テスト条件: 変化レベル {change_levels}")
    print("=" * 70)
    
    results = []
    
    for change_level in change_levels:
        print(f"\n【テスト {change_level}】 変化レベル: {change_level}")
        print("-" * 70)
        
        start_time = time.time()
        
        try:
            result = process_youtube_to_presentation(
                url=url,
                change_level=change_level
            )
            
            elapsed_time = time.time() - start_time
            slide_count = len(result['scenes'])
            
            results.append({
                'change_level': change_level,
                'elapsed_time': elapsed_time,
                'slide_count': slide_count,
                'success': True
            })
            
            print(f"✅ 処理成功")
            print(f"   処理時間: {elapsed_time:.1f}秒")
            print(f"   抽出スライド数: {slide_count}枚")
            print(f"   1スライドあたりの平均時間: {elapsed_time/slide_count:.2f}秒")
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            results.append({
                'change_level': change_level,
                'elapsed_time': elapsed_time,
                'slide_count': 0,
                'success': False,
                'error': str(e)
            })
            print(f"❌ エラーが発生しました")
            print(f"   実行時間: {elapsed_time:.1f}秒")
            print(f"   エラー: {e}")
    
    # 結果のサマリー表示
    print("\n" + "=" * 70)
    print("ベンチマーク結果サマリー")
    print("=" * 70)
    print(f"{'変化レベル':<15} {'処理時間':<15} {'スライド数':<15} {'平均時間/枚':<15}")
    print("-" * 70)
    
    for r in results:
        if r['success']:
            avg_time = r['elapsed_time'] / r['slide_count'] if r['slide_count'] > 0 else 0
            print(f"{r['change_level']:<15} {r['elapsed_time']:<14.1f}s {r['slide_count']:<15} {avg_time:<14.2f}s")
        else:
            print(f"{r['change_level']:<15} {'エラー':<14} - {'error':<15}")
    
    # 最速・最遅の比較
    success_results = [r for r in results if r['success']]
    if success_results:
        fastest = min(success_results, key=lambda x: x['elapsed_time'])
        slowest = max(success_results, key=lambda x: x['elapsed_time'])
        
        print("\n" + "-" * 70)
        print(f"🏃 最速: 変化レベル {fastest['change_level']} - {fastest['elapsed_time']:.1f}秒")
        print(f"🐢 最遅: 変化レベル {slowest['change_level']} - {slowest['elapsed_time']:.1f}秒")
        print(f"   差分: {slowest['elapsed_time'] - fastest['elapsed_time']:.1f}秒 ({((slowest['elapsed_time'] - fastest['elapsed_time']) / fastest['elapsed_time'] * 100):.1f}%)")


def profile_single_video(url: str, change_level: int = 5):
    """
    単一の動画をプロファイリングし、詳細な処理時間を測定する。
    
    Parameters
    ----------
    url : str
        YouTube動画のURL
    change_level : int
        変化レベル（1-10）
    """
    print("=" * 70)
    print("YouTube Iフレーム抽出 - 詳細プロファイリング")
    print("=" * 70)
    print(f"テストURL: {url}")
    print(f"変化レベル: {change_level}")
    print("=" * 70)
    
    start_time = time.time()
    
    try:
        result = process_youtube_to_presentation(
            url=url,
            change_level=change_level
        )
        
        total_time = time.time() - start_time
        slide_count = len(result['scenes'])
        
        print(f"\n✅ 処理成功")
        print(f"   総処理時間: {total_time:.1f}秒")
        print(f"   抽出スライド数: {slide_count}枚")
        print(f"   1スライドあたり: {total_time/slide_count:.2f}秒")
        print(f"   動画タイトル: {result['title']}")
        print(f"   字幕の有無: {'あり' if result['has_transcript'] else 'なし'}")
        
        if slide_count > 0:
            print(f"\n抽出されたスライド一覧:")
            for i, scene in enumerate(result['scenes'][:5]):  # 最初の5枚を表示
                minutes = int(scene['timestamp'] // 60)
                seconds = int(scene['timestamp'] % 60)
                text_preview = scene['text'][:50] + "..." if len(scene['text']) > 50 else scene['text']
                print(f"  [{i+1}] {minutes:02d}:{seconds:02d} - {text_preview}")
            if slide_count > 5:
                print(f"  ... 他 {slide_count - 5} 枚")
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n❌ エラーが発生しました")
        print(f"   実行時間: {elapsed_time:.1f}秒")
        print(f"   エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python benchmark_iframe_extraction.py <YouTube URL> [--benchmark] [--profile]")
        print()
        print("引数:")
        print("  <YouTube URL>     処理対象のYouTube動画URL")
        print("  --benchmark       複数の変化レベルでベンチマーク実行（デフォルト）")
        print("  --profile         単一動画の詳細プロファイリング")
        print()
        print("例:")
        print("  python benchmark_iframe_extraction.py 'https://www.youtube.com/watch?v=QqArUuwDpxU'")
        print("  python benchmark_iframe_extraction.py 'https://www.youtube.com/watch?v=QqArUuwDpxU' --profile")
        sys.exit(1)
    
    url = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "--benchmark"
    
    try:
        if mode == "--profile":
            profile_single_video(url, change_level=5)
        else:
            benchmark_video_processing(url, change_levels=[3, 5, 7])
    except KeyboardInterrupt:
        print("\n\n⏸️  処理が中断されました")
        sys.exit(1)
