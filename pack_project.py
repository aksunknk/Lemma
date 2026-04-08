import os
import zipfile

def pack_project():
    output_filename = "project_core.zip"
    exclude_dirs = {
        'node_modules', '.venv', 'venv', '__pycache__', '.git', '.next', 'dist'
    }
    exclude_files = {'.DS_Store', output_filename}
    include_extensions = {'.task', '.walkthrough'}
    
    current_dir = os.path.abspath(os.path.dirname(__file__))
    
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(current_dir):
            # 除外対象ディレクトリ配下の走査を制御
            # ただし、要件3により「深さを問わず確実に含める」必要があるため、
            # 除外ディレクトリ内であっても特定の拡張子を持つファイルがあるかチェックする
            
            # ディレクトリ名のチェック
            dir_name = os.path.basename(root)
            is_in_exclude_dir = any(ex in root.split(os.sep) for ex in exclude_dirs)
            
            for file in files:
                # 自身（ZIPファイル）は除外
                if file == output_filename:
                    continue
                
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1]
                
                # 除外対象ファイル（.DS_Storeなど）は常に除外
                if file in exclude_files:
                    continue

                # 判定ロジック:
                # 1. 必須拡張子 (.task, .walkthrough) なら無条件で追加
                # 2. 除外ディレクトリ外なら通常通り追加
                if file_ext in include_extensions or not is_in_exclude_dir:
                    arcname = os.path.relpath(file_path, current_dir)
                    zipf.write(file_path, arcname)
    
    if os.path.exists(output_filename):
        size_mb = os.path.getsize(output_filename) / (1024 * 1024)
        print(f"ZIP化完了: {output_filename} (約 {size_mb:.2f} MB)")
    else:
        print("エラー: アーカイブの作成に失敗しました。")

if __name__ == "__main__":
    pack_project()
