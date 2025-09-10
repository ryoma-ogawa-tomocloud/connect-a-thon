#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Storage Commitment Request テスト
AMからIMに対してStorage Commitment Request（N-ACTION）
"""

import logging
import time
import socket
from datetime import datetime
from pynetdicom import AE
from pydicom.dataset import Dataset
from pydicom.uid import generate_uid

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StorageCommitmentClient:
    """Storage Commitment Request クライアント"""
    
    def __init__(self):
        self.am_aet = "LTMONITOR"
        self.im_aet = "IM" 
        self.im_ip = "127.0.0.1"
        self.im_port = 11113  # IMサーバーのポート
        
        # Implementation情報（image_store_testと同じ）
        self.implementation_class_uid = "1.2.392.200036.8120.101.9"
        self.implementation_version = "Monocube1.0.0.0"
    
    def create_commitment_ae(self):
        """Storage Commitment用AE作成"""
        ae = AE(ae_title=self.am_aet)
        ae.implementation_class_uid = self.implementation_class_uid
        ae.implementation_version_name = self.implementation_version
        
        # Storage Commitment Push Model SOP Class
        storage_commitment_uid = '1.2.840.10008.1.20.1'  # Storage Commitment Push Model
        
        # Transfer Syntaxes（image_store_testと同じ）
        transfer_syntaxes = [
            '1.2.840.10008.1.2',        # Implicit VR Little Endian
            '1.2.840.10008.1.2.1',      # Explicit VR Little Endian  
            '1.2.840.10008.1.2.2',      # Explicit VR Big Endian
        ]
        
        # Storage Commitment用のPresentation Contextを追加
        ae.add_requested_context(storage_commitment_uid, transfer_syntaxes)
        
        ae.maximum_pdu_size = 16384
        ae.network_timeout = 10
        ae.acse_timeout = 10
        ae.dimse_timeout = 30
        
        logger.info("=== 登録されたPresentation Context ===")
        logger.info(f"SOP Class: Storage Commitment Push Model")
        logger.info(f"Transfer Syntaxes:")
        for i, ts in enumerate(transfer_syntaxes, 1):
            ts_name = {
                '1.2.840.10008.1.2': 'Implicit VR Little Endian',
                '1.2.840.10008.1.2.1': 'Explicit VR Little Endian',
                '1.2.840.10008.1.2.2': 'Explicit VR Big Endian'
            }.get(ts, 'Unknown')
            logger.info(f"  {i}. {ts_name} ({ts})")
        logger.info("=====================================")
        
        return ae
    
    def create_commitment_request(self, sop_class_uid=None, sop_instance_uid=None):
        """Storage Commitment Request作成"""
        print("Storage Commitment Requestを作成中...")
        
        # N-ACTION Request用のDataset作成
        ds = Dataset()
        
        # 文字セット指定（MWLテスト・image_store_testと同じ）
        ds.SpecificCharacterSet = ['ISO 2022 IR 6', 'ISO 2022 IR 87']
        
        # Storage Commitment Transaction UID
        ds.TransactionUID = generate_uid()
        
        # Referenced SOP Sequence（保存済み画像の参照）
        ref_sop_item = Dataset()
        ref_sop_item.ReferencedSOPClassUID = sop_class_uid or '1.2.840.10008.5.1.4.1.1.7'  # Secondary Capture
        ref_sop_item.ReferencedSOPInstanceUID = sop_instance_uid or generate_uid()  # 実際の保存済み画像のUID
        
        ds.ReferencedSOPSequence = [ref_sop_item]
        
        print(f"作成したStorage Commitment Request:")
        print(f"  TransactionUID: {ds.TransactionUID}")
        print(f"  ReferencedSOPClassUID: {ref_sop_item.ReferencedSOPClassUID}")
        print(f"  ReferencedSOPInstanceUID: {ref_sop_item.ReferencedSOPInstanceUID}")
        
        return ds
    
    def test_storage_commitment(self):
        """Storage Commitment Request テスト"""
        logger.info("=== Storage Commitment Request テスト ===")
        
        try:
            # AE作成
            ae = self.create_commitment_ae()
            
            # IMサーバーに接続
            logger.info(f"IMサーバーに接続中: {self.im_ip}:{self.im_port} (AET: {self.im_aet})")
            assoc = ae.associate(self.im_ip, self.im_port, ae_title=self.im_aet)
            
            if not assoc.is_established:
                logger.error("IMサーバーとのアソシエーション確立失敗")
                return False
            
            logger.info("OK: IMアソシエーション確立成功")
            logger.info(f"アクセプト済み: {[ctx.abstract_syntax for ctx in assoc.accepted_contexts]}")
            
            # Storage Commitment Request作成
            # 実際に保存された画像のUIDを使用（手動設定）
            test_sop_class_uid = '1.2.840.10008.5.1.4.1.1.7'  # Secondary Capture
            test_sop_instance_uid = '1.2.826.0.1.3680043.8.498.71417461484991112270844658039110027518'  # image_store_testで保存されたUID
            request_dataset = self.create_commitment_request(test_sop_class_uid, test_sop_instance_uid)
            
            # N-ACTION送信
            logger.info("N-ACTION送信中...")
            
            try:
                # Storage Commitment Push Model SOP Class
                sop_class_uid = '1.2.840.10008.1.20.1'
                # Storage Commitment Request SOP Instance UID  
                sop_instance_uid = '1.2.840.10008.1.20.1.1'
                # Storage Commitment Request Action Type ID (integer)
                action_type_id = 1  # Request Storage Commitment
                
                status = assoc.send_n_action(
                    request_dataset,
                    action_type_id,
                    sop_class_uid,
                    sop_instance_uid  # 専用のSOP Instance UID
                )
                
                if status:
                    logger.info(f"N-ACTIONレスポンス: {type(status)}")
                    
                    # statusがタプルの場合の処理
                    if isinstance(status, tuple) and len(status) >= 1:
                        status_ds = status[0]
                        if hasattr(status_ds, 'Status'):
                            status_code = status_ds.Status
                            logger.info(f"ステータスコード: 0x{status_code:04X}")
                            
                            if status_code == 0x0000:  # Success
                                logger.info("OK: N-ACTION成功")
                                logger.info("Storage Commitment Requestが正常に送信されました")
                                success = True
                            else:
                                logger.warning(f"N-ACTION警告: ステータス 0x{status_code:04X}")
                                success = False
                        else:
                            logger.info(f"ステータスデータセット: {status_ds}")
                            success = True
                    elif hasattr(status, 'Status'):
                        status_code = status.Status
                        logger.info(f"ステータスコード: 0x{status_code:04X}")
                        
                        if status_code == 0x0000:  # Success
                            logger.info("OK: N-ACTION成功")
                            logger.info("Storage Commitment Requestが正常に送信されました")
                            success = True
                        else:
                            logger.warning(f"N-ACTION警告: ステータス 0x{status_code:04X}")
                            success = False
                    else:
                        logger.info("ステータス情報なし")
                        success = status is not None
                else:
                    logger.error("N-ACTION失敗: レスポンスなし")
                    success = False
                    
            except Exception as action_error:
                logger.error(f"N-ACTION送信エラー: {action_error}")
                success = False
            
            # アソシエーション終了
            assoc.release()
            logger.info("アソシエーション終了")
            
            return success
            
        except Exception as e:
            logger.error(f"Storage Commitment接続エラー: {e}")
            return False
    
    def monitor_and_request(self):
        """IMサーバー監視＆Storage Commitment Request実行"""
        print("=== Storage Commitment Request システム ===")
        print(f"送信元: {self.am_aet}")
        print(f"送信先: {self.im_aet} ({self.im_ip}:{self.im_port})")
        print()
        print("IMサーバー監視中...")
        print("コネクタソンツールでIMテストを開始してください")
        
        # サーバー監視
        max_wait = 60
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                sock = socket.create_connection((self.im_ip, self.im_port), timeout=0.5)
                sock.close()
                
                print(f"\\nOK: IMサーバー検出！({time.time() - start_time:.1f}秒後)")
                print("Storage Commitment RequestをImage Managerに送信します...")
                
                success = self.test_storage_commitment()
                
                if success:
                    print("OK: Storage Commitment Request成功！")
                    print("Storage Commitment RequestがImage Managerに正常に送信されました")
                    return True
                else:
                    print("NG: Storage Commitment Requestに問題がありました")
                    return False
                    
            except socket.error:
                pass
            
            time.sleep(0.5)
            print(".", end="", flush=True)
        
        print()
        print("NG: IMサーバーが制限時間内に起動しませんでした")
        return False

def main():
    """メイン実行"""
    print("Storage Commitment Request テスト")
    print("=================================")
    print("1. 監視モード（IMサーバー自動検出）")
    print("2. 直接テスト（即座に実行）")
    
    choice = input("選択 (1-2): ").strip()
    
    client = StorageCommitmentClient()
    
    if choice == "2":
        print("直接テストを実行します...")
        success = client.test_storage_commitment()
        if success:
            print("OK: 直接テスト成功")
        else:
            print("NG: 直接テスト失敗")
    else:
        print("監視モードを開始します...")
        client.monitor_and_request()

if __name__ == "__main__":
    main()