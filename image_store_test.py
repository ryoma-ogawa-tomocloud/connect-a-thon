#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Manager画像保存テスト
AMからIMに対してDICOM画像を送信（C-STORE）
"""

import logging
import time
import socket
from datetime import datetime
from pynetdicom import AE
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import generate_uid
from pydicom import dcmread
import tempfile
import os

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageStoreClient:
    """Image Manager画像保存クライアント"""
    
    def __init__(self):
        self.am_aet = "LTMONITOR"
        self.im_aet = "IM" 
        self.im_ip = "127.0.0.1"
        self.im_port = 11113  # IMサーバーのポート
        
        # Implementation情報（OFサーバーと一致）
        self.implementation_class_uid = "1.2.392.200036.8120.101.9"
        self.implementation_version = "Monocube1.0.0.0"
    
    def create_store_ae(self):
        """C-STORE用AE作成（Secondary Capture専用）"""
        ae = AE(ae_title=self.am_aet)
        ae.implementation_class_uid = self.implementation_class_uid
        ae.implementation_version_name = self.implementation_version
        
        # Secondary Capture Image Storage専用
        secondary_capture_uid = '1.2.840.10008.5.1.4.1.1.7'  # Secondary Capture Image Storage
        
        # 提供された Transfer Syntax 一覧に基づいて設定
        transfer_syntaxes = [
            '1.2.840.10008.1.2',        # Implicit VR Little Endian
            '1.2.840.10008.1.2.1',      # Explicit VR Little Endian  
            '1.2.840.10008.1.2.2',      # Explicit VR Big Endian
            '1.2.840.10008.1.2.4.50',   # JPEG Lossy Baseline
            '1.2.840.10008.1.2.4.70'    # JPEG Lossy
        ]
        
        # Secondary Capture用のPresentation Contextを追加
        ae.add_requested_context(secondary_capture_uid, transfer_syntaxes)
        
        ae.maximum_pdu_size = 16384
        ae.network_timeout = 10
        ae.acse_timeout = 10
        ae.dimse_timeout = 30
        
        logger.info("=== 登録されたPresentation Context ===")
        logger.info(f"SOP Class: Secondary Capture Image Storage")
        logger.info(f"Transfer Syntaxes:")
        for i, ts in enumerate(transfer_syntaxes, 1):
            ts_name = {
                '1.2.840.10008.1.2': 'Implicit VR Little Endian',
                '1.2.840.10008.1.2.1': 'Explicit VR Little Endian',
                '1.2.840.10008.1.2.2': 'Explicit VR Big Endian', 
                '1.2.840.10008.1.2.4.50': 'JPEG Lossy Baseline',
                '1.2.840.10008.1.2.4.70': 'JPEG Lossy'
            }.get(ts, 'Unknown')
            logger.info(f"  {i}. {ts_name} ({ts})")
        logger.info("=====================================")
        
        return ae
    
    def create_sample_dicom_image(self):
        """サンプルDICOM画像作成"""
        print("サンプルDICOM画像を作成中...")
        
        # File Meta Information作成
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.7'  # Secondary Capture
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.ImplementationClassUID = self.implementation_class_uid
        file_meta.ImplementationVersionName = self.implementation_version
        file_meta.TransferSyntaxUID = '1.2.840.10008.1.2'  # Implicit VR Little Endian
        
        # FileDatasetとして作成
        ds = FileDataset("temp", {}, file_meta=file_meta, preamble=b"\0" * 128)
        
        # 文字セット指定（MWLテストと同じ）
        ds.SpecificCharacterSet = ['ISO 2022 IR 6', 'ISO 2022 IR 87']
        
        # Patient Module
        ds.PatientName = "FUKUOKA^CHIHIRO=福岡^千尋=フクオカ^チヒロ"
        ds.PatientID = "1234567890"
        ds.PatientBirthDate = "19800502"
        ds.PatientSex = "M"
        
        # General Study Module
        ds.StudyInstanceUID = generate_uid()
        ds.StudyDate = datetime.now().strftime("%Y%m%d")
        ds.StudyTime = datetime.now().strftime("%H%M%S")
        ds.ReferringPhysicianName = ""
        ds.StudyID = "1"
        ds.AccessionNumber = "A20110730123000"
        
        # General Series Module
        ds.SeriesInstanceUID = generate_uid()
        ds.SeriesNumber = "1"
        ds.SeriesDate = datetime.now().strftime("%Y%m%d")
        ds.SeriesTime = datetime.now().strftime("%H%M%S")
        ds.Modality = "OT"  # Other
        
        # General Image Module
        ds.InstanceNumber = "1"
        ds.ImageDate = datetime.now().strftime("%Y%m%d")
        ds.ImageTime = datetime.now().strftime("%H%M%S")
        
        # SOP Common Module
        ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
        
        # SC Equipment Module
        ds.ConversionType = "WSD"  # Workstation
        ds.SecondaryCaptureDeviceManufacturer = "Test Equipment"
        ds.SecondaryCaptureDeviceManufacturerModelName = "Test Model"
        
        # Image Pixel Module（小さなダミー画像）
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.Rows = 64
        ds.Columns = 64
        ds.BitsAllocated = 8
        ds.BitsStored = 8
        ds.HighBit = 7
        ds.PixelRepresentation = 0
        
        # ダミーピクセルデータ（64x64の8bitグレースケール）
        import numpy as np
        pixel_array = np.random.randint(0, 256, (64, 64), dtype=np.uint8)
        ds.PixelData = pixel_array.tobytes()
        
        print(f"作成したDICOM画像:")
        print(f"  PatientName: {ds.PatientName}")
        print(f"  PatientID: {ds.PatientID}")
        print(f"  StudyInstanceUID: {ds.StudyInstanceUID}")
        print(f"  SeriesInstanceUID: {ds.SeriesInstanceUID}")
        print(f"  SOPInstanceUID: {ds.SOPInstanceUID}")
        print(f"  Modality: {ds.Modality}")
        print(f"  画像サイズ: {ds.Rows}x{ds.Columns}")
        
        return ds
    
    def save_temp_dicom_file(self, dataset):
        """一時的なDICOMファイルとして保存"""
        temp_dir = tempfile.gettempdir()
        temp_filename = f"temp_dicom_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dcm"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        # File Meta Information
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = dataset.SOPClassUID
        file_meta.MediaStorageSOPInstanceUID = dataset.SOPInstanceUID
        file_meta.ImplementationClassUID = self.implementation_class_uid
        file_meta.ImplementationVersionName = self.implementation_version
        file_meta.TransferSyntaxUID = '1.2.840.10008.1.2'  # Implicit VR Little Endian
        
        # FileDataset作成
        file_dataset = FileDataset(temp_path, dataset, file_meta=file_meta, preamble=b"\\0" * 128)
        
        # ファイル保存
        file_dataset.save_as(temp_path)
        print(f"一時DICOMファイル保存: {temp_path}")
        
        return temp_path
    
    def test_image_store(self):
        """Image Manager画像保存テスト"""
        logger.info("=== Image Manager画像保存テスト ===")
        
        try:
            # AE作成
            ae = self.create_store_ae()
            
            # IMサーバーに接続
            logger.info(f"IMサーバーに接続中: {self.im_ip}:{self.im_port} (AET: {self.im_aet})")
            assoc = ae.associate(self.im_ip, self.im_port, ae_title=self.im_aet)
            
            if not assoc.is_established:
                logger.error("IMサーバーとのアソシエーション確立失敗")
                return False
            
            logger.info("OK: IMアソシエーション確立成功")
            logger.info(f"アクセプト済み: {[ctx.abstract_syntax for ctx in assoc.accepted_contexts]}")
            
            # サンプル画像作成
            image_dataset = self.create_sample_dicom_image()
            
            # C-STORE送信
            logger.info("C-STORE送信中...")
            
            try:
                status = assoc.send_c_store(image_dataset)
                
                if status:
                    logger.info(f"C-STOREレスポンス: {type(status)}")
                    
                    if hasattr(status, 'Status'):
                        status_code = status.Status
                        logger.info(f"ステータスコード: 0x{status_code:04X}")
                        
                        if status_code == 0x0000:  # Success
                            logger.info("OK: C-STORE成功")
                            logger.info("画像がImage Managerに正常に保存されました")
                            success = True
                        else:
                            logger.warning(f"C-STORE警告: ステータス 0x{status_code:04X}")
                            success = False
                    else:
                        logger.info("ステータス情報なし")
                        success = status is not None
                else:
                    logger.error("C-STORE失敗: レスポンスなし")
                    success = False
                    
            except Exception as store_error:
                logger.error(f"C-STORE送信エラー: {store_error}")
                success = False
            
            # アソシエーション終了
            assoc.release()
            logger.info("アソシエーション終了")
            
            return success
            
        except Exception as e:
            logger.error(f"Image Store接続エラー: {e}")
            return False
    
    def monitor_and_store(self):
        """IMサーバー監視＆画像保存実行"""
        print("=== Image Manager画像保存システム ===")
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
                print("DICOM画像をImage Managerに送信します...")
                
                success = self.test_image_store()
                
                if success:
                    print("OK: 画像保存成功！")
                    print("DICOM画像がImage Managerに正常に保存されました")
                    return True
                else:
                    print("NG: 画像保存に問題がありました")
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
    print("Image Manager画像保存テスト")
    print("===========================")
    print("1. 監視モード（IMサーバー自動検出）")
    print("2. 直接テスト（即座に実行）")
    
    choice = input("選択 (1-2): ").strip()
    
    client = ImageStoreClient()
    
    if choice == "2":
        print("直接テストを実行します...")
        success = client.test_image_store()
        if success:
            print("OK: 直接テスト成功")
        else:
            print("NG: 直接テスト失敗")
    else:
        print("監視モードを開始します...")
        client.monitor_and_store()

if __name__ == "__main__":
    main()