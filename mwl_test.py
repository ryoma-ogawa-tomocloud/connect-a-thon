#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
シンプルなMWLテストクライアント
最小限の設定でOFサーバーとの互換性を確認
"""

import logging
import time
from pynetdicom import AE, debug_logger
from pydicom.dataset import Dataset

# デバッグログを有効にしてプロトコルレベルの詳細を確認
debug_logger()
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_minimal_mwl_client():
    """最小限のMWLクライアント作成"""
    # 最もシンプルな設定
    ae = AE(ae_title="LTMONITOR")
    
    # MWL SOP Classのみ
    mwl_uid = '1.2.840.10008.5.1.4.31'
    ae.add_requested_context(mwl_uid)
    
    # 最小限のPDUサイズ（互換性重視）
    ae.maximum_pdu_size = 4096
    
    # 短いタイムアウト
    ae.network_timeout = 5
    ae.acse_timeout = 5
    ae.dimse_timeout = 10
    
    return ae

def create_simple_mwl_query():
    """シンプルなMWLクエリ作成（OFサーバー互換）"""
    ds = Dataset()
    
    # 文字セット指定（日本語対応）- OFサーバーが要求するタグ
    # 成功したオプション1のみを使用
    ds.SpecificCharacterSet = ['ISO 2022 IR 6', 'ISO 2022 IR 87']  # ASCII + JIS X 0208
    
    # 患者情報（検索条件）
    ds.PatientName = "*"  # ワイルドカード検索
    ds.PatientID = "*"    # ワイルドカード検索
    ds.PatientBirthDate = ""
    ds.PatientSex = ""
    
    # 検査情報
    ds.StudyInstanceUID = ""
    ds.AccessionNumber = "*"  # ワイルドカード検索
    ds.RequestingPhysician = ""
    
    # Scheduled Procedure Step Sequence（必須）
    sps_item = Dataset()
    
    # OFサーバーが要求する必須フィールドに値を設定
    sps_item.Modality = "CR"  # ← 必須: 空でなく具体的な値
    sps_item.ScheduledStationAETitle = "LTMONITOR"
    
    # 日付を具体的に設定（今日の日付）
    from datetime import datetime
    today = datetime.now()
    sps_item.ScheduledProcedureStepStartDate = today.strftime("%Y%m%d")  # ← 必須: 空でなく具体的な値
    sps_item.ScheduledProcedureStepStartTime = "080000"  # 08:00:00
    
    sps_item.ScheduledProcedureStepID = "*"  # ワイルドカード検索
    sps_item.ScheduledProcedureStepDescription = ""
    
    ds.ScheduledProcedureStepSequence = [sps_item]
    
    print(f"作成したMWLクエリ:")
    print(f"  SpecificCharacterSet: {ds.SpecificCharacterSet}")
    print(f"  Modality: {sps_item.Modality}")
    print(f"  ScheduledProcedureStepStartDate: {sps_item.ScheduledProcedureStepStartDate}")
    print(f"  PatientName: {ds.PatientName}")
    print(f"  PatientID: {ds.PatientID}")
    print(f"  AccessionNumber: {ds.AccessionNumber}")
    
    return ds

def test_of_connection():
    """OFサーバー接続テスト"""
    print("シンプルMWLテスト開始")
    print("=" * 30)
    
    # 設定
    of_ip = "127.0.0.1"
    of_port = 11114
    of_aet = "OF"
    
    # クライアント作成
    ae = create_minimal_mwl_client()
    
    try:
        print(f"接続中: {of_ip}:{of_port} (AET: {of_aet})")
        
        # アソシエーション確立
        assoc = ae.associate(of_ip, of_port, ae_title=of_aet)
        
        if assoc.is_established:
            print("OK: アソシエーション確立成功")
            
            # MWLクエリ送信
            query_ds = create_simple_mwl_query()
            mwl_uid = '1.2.840.10008.5.1.4.31'
            
            print("MWLクエリ送信中...")
            
            try:
                responses_iterator = assoc.send_c_find(query_ds, mwl_uid)
                
                if responses_iterator is None:
                    print("NG: C-FIND送信失敗 - None応答")
                    assoc.release()
                    return False
                
                if isinstance(responses_iterator, bool):
                    print(f"NG: C-FIND送信失敗 - bool応答: {responses_iterator}")
                    assoc.release()
                    return False
                
                responses = list(responses_iterator)
                print(f"応答数: {len(responses)}")
                
                if len(responses) == 0:
                    print("応答なし - サーバーが接続を切断した可能性")
                    return False
                
                worklist_count = 0
                
                for i, response in enumerate(responses):
                    print(f"応答 {i+1}: {type(response)}")
                    
                    # responseがタプルかチェック
                    if isinstance(response, tuple) and len(response) == 2:
                        status, identifier = response
                        
                        # statusがDatasetの場合の処理
                        if hasattr(status, 'Status'):
                            status_code = status.Status
                            print(f"  Status=0x{status_code:04X}")
                            
                            if identifier is not None:
                                worklist_count += 1
                                patient_name = getattr(identifier, 'PatientName', 'Unknown')
                                patient_id = getattr(identifier, 'PatientID', 'Unknown')
                                accession = getattr(identifier, 'AccessionNumber', 'Unknown')
                                
                                print(f"  ワークリスト {worklist_count}:")
                                print(f"    患者名: {patient_name}")
                                print(f"    患者ID: {patient_id}")
                                print(f"    受付番号: {accession}")
                                
                                # Scheduled Procedure Step情報
                                if hasattr(identifier, 'ScheduledProcedureStepSequence') and identifier.ScheduledProcedureStepSequence:
                                    sps = identifier.ScheduledProcedureStepSequence[0]
                                    modality = getattr(sps, 'Modality', 'Unknown')
                                    date = getattr(sps, 'ScheduledProcedureStepStartDate', 'Unknown')
                                    time_val = getattr(sps, 'ScheduledProcedureStepStartTime', 'Unknown')
                                    
                                    print(f"    モダリティ: {modality}")
                                    print(f"    予定日時: {date} {time_val}")
                            
                            # ステータスチェック
                            if status_code == 0x0000:  # Success
                                print("  C-FIND完了")
                                break
                            elif status_code == 0xFF00:  # Pending
                                print("  応答待機中...")
                                continue
                            else:
                                print(f"  予期しないステータス: 0x{status_code:04X}")
                        
                        elif hasattr(status, '__iter__'):
                            # statusがDatasetオブジェクトの場合
                            print(f"  Status情報: {status}")
                        else:
                            print(f"  Status型: {type(status)}")
                        
                    else:
                        print(f"  予期しない応答形式: {response}")
                
                print(f"\\n✓ MWLクエリ成功: {worklist_count}件のワークリスト取得")
                        
            except Exception as response_error:
                print(f"応答処理エラー: {response_error}")
                print(f"エラータイプ: {type(response_error)}")
                return False
            
            # アソシエーション終了
            assoc.release()
            print("OK: テスト完了")
            return True
            
        else:
            print("NG: アソシエーション確立失敗")
            return False
            
    except Exception as e:
        print(f"NG: エラー: {e}")
        print(f"エラータイプ: {type(e).__name__}")
        return False

if __name__ == "__main__":
    test_of_connection()