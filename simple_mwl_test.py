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
    """シンプルなMWLクエリ作成"""
    ds = Dataset()
    
    # 必要最小限のフィールドのみ
    ds.PatientName = ""
    ds.PatientID = ""
    
    # Scheduled Procedure Step Sequence（必須）
    sps_item = Dataset()
    sps_item.Modality = ""
    sps_item.ScheduledStationAETitle = "LTMONITOR"
    sps_item.ScheduledProcedureStepStartDate = ""
    sps_item.ScheduledProcedureStepStartTime = ""
    sps_item.ScheduledProcedureStepID = ""
    
    ds.ScheduledProcedureStepSequence = [sps_item]
    
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
                
                for i, response in enumerate(responses):
                    print(f"応答 {i+1}: {type(response)}")
                    
                    # responseがタプルかチェック
                    if isinstance(response, tuple) and len(response) == 2:
                        status, identifier = response
                        
                        # statusがDatasetの場合の処理
                        if hasattr(status, 'Status'):
                            print(f"  Status=0x{status.Status:04X}")
                        elif hasattr(status, '__iter__'):
                            # statusがDatasetオブジェクトの場合
                            print(f"  Status情報: {status}")
                        else:
                            print(f"  Status型: {type(status)}")
                        
                        if identifier:
                            patient_name = getattr(identifier, 'PatientName', 'N/A')
                            print(f"  患者名: {patient_name}")
                    else:
                        print(f"  予期しない応答形式: {response}")
                        
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