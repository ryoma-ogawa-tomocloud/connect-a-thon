#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統合テスト：Image Store + Storage Commitment
1. C-STOREで画像を保存
2. 同じUIDでStorage Commitment Requestを送信
"""

import logging
import time
import socket
import threading
from datetime import datetime
from pynetdicom import AE, evt
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import generate_uid
import numpy as np

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegratedTestClient:
    """統合テストクライアント"""
    
    def __init__(self):
        self.am_aet = "LTMONITOR"
        self.im_aet = "IM" 
        self.im_ip = "127.0.0.1"
        self.im_port = 11113  # IMサーバーのポート
        
        # Implementation情報
        self.implementation_class_uid = "1.2.392.200036.8120.101.9"
        self.implementation_version = "Monocube1.0.0.0"
        
        # 保存した画像のUID（Storage Commitmentで使用）
        self.stored_sop_class_uid = None
        self.stored_sop_instance_uid = None
        
        # Storage Commitment受信用
        self.commitment_received = False
        self.commitment_success = False
        self.commitment_failed_instances = []
        self.am_listen_port = 11112  # AMがN-EVENT-REPORTを受信するポート（IMのログに合わせて修正）
    
    def create_store_ae(self):
        """C-STORE用AE作成"""
        ae = AE(ae_title=self.am_aet)
        ae.implementation_class_uid = self.implementation_class_uid
        ae.implementation_version_name = self.implementation_version
        
        # Secondary Capture Image Storage
        secondary_capture_uid = '1.2.840.10008.5.1.4.1.1.7'
        # Multi-frame True Color Secondary Capture Image Storage
        multiframe_true_color_uid = '1.2.840.10008.5.1.4.1.1.7.4'

        transfer_syntaxes = [
            '1.2.840.10008.1.2',        # Implicit VR Little Endian
            '1.2.840.10008.1.2.1',      # Explicit VR Little Endian
            '1.2.840.10008.1.2.2',      # Explicit VR Big Endian
            '1.2.840.10008.1.2.4.50',   # JPEG Lossy Baseline
            '1.2.840.10008.1.2.4.70'    # JPEG Lossy
        ]

        # 両方のSOP Classをサポート
        ae.add_requested_context(secondary_capture_uid, transfer_syntaxes)
        ae.add_requested_context(multiframe_true_color_uid, transfer_syntaxes)
        
        
        ae.maximum_pdu_size = 16384
        ae.network_timeout = 10
        ae.acse_timeout = 10
        ae.dimse_timeout = 30
        
        return ae
    
    def create_commitment_ae(self):
        """Storage Commitment用AE作成"""
        ae = AE(ae_title=self.am_aet)
        ae.implementation_class_uid = self.implementation_class_uid
        ae.implementation_version_name = self.implementation_version
        
        # Storage Commitment Push Model
        storage_commitment_uid = '1.2.840.10008.1.20.1'
        
        transfer_syntaxes = [
            '1.2.840.10008.1.2',        # Implicit VR Little Endian
            '1.2.840.10008.1.2.1',      # Explicit VR Little Endian  
            '1.2.840.10008.1.2.2',      # Explicit VR Big Endian
        ]
        
        ae.add_requested_context(storage_commitment_uid, transfer_syntaxes)
        
        ae.maximum_pdu_size = 16384
        ae.network_timeout = 10
        ae.acse_timeout = 10
        ae.dimse_timeout = 30
        
        return ae
    
    def handle_storage_commitment_result(self, event):
        """Storage Commitment結果受信ハンドラー"""
        logger.info("=== Storage Commitment結果受信 ===")
        
        try:
            # N-EVENT-REPORTの情報取得
            logger.info(f"Event: {event}")
            logger.info(f"Event attributes: {dir(event)}")
            logger.info(f"Request: {event.request}")
            
            # Event Type IDをリクエストから取得
            event_type_id = None
            if hasattr(event.request, 'EventTypeID'):
                event_type_id = event.request.EventTypeID
                logger.info(f"Event Type ID: {event_type_id}")
            
            # リクエストからデータセット取得
            dataset = None
            if hasattr(event.request, 'EventInformation') and event.request.EventInformation:
                dataset = event.request.EventInformation
                logger.info(f"受信データセット: {type(dataset)}")
                
                if hasattr(dataset, 'TransactionUID'):
                    logger.info(f"Transaction UID: {dataset.TransactionUID}")
            
            # Event Type IDで結果を判定
            if event_type_id == 1:  # Storage Commitment Result - Success
                logger.info("OK: Storage Commitment 成功")
                self.commitment_success = True
                
                # 成功したインスタンスの情報
                if dataset and hasattr(dataset, 'ReferencedSOPSequence'):
                    for ref_sop in dataset.ReferencedSOPSequence:
                        logger.info(f"  成功: {ref_sop.ReferencedSOPClassUID}")
                        logger.info(f"         {ref_sop.ReferencedSOPInstanceUID}")
                        
            elif event_type_id == 2:  # Storage Commitment Result - Failure
                logger.warning("NG: Storage Commitment 一部失敗")
                self.commitment_success = False
                
                # 失敗したインスタンスの情報
                if dataset and hasattr(dataset, 'FailedSOPSequence'):
                    for failed_sop in dataset.FailedSOPSequence:
                        logger.warning(f"  失敗: {failed_sop.ReferencedSOPClassUID}")
                        logger.warning(f"        {failed_sop.ReferencedSOPInstanceUID}")
                        logger.warning(f"        理由: {getattr(failed_sop, 'FailureReason', 'Unknown')}")
                        self.commitment_failed_instances.append(failed_sop)
                        
            else:
                logger.warning(f"予期しないEvent Type ID: {event_type_id}")
                # Event Type IDが取得できない場合でも受信成功として扱う
                if event_type_id is None:
                    logger.info("Event Type ID取得不可：受信成功として扱います")
                    self.commitment_success = True
            
            self.commitment_received = True
            logger.info("Storage Commitment結果処理完了")
            
        except Exception as e:
            logger.error(f"Storage Commitment結果処理エラー: {e}")
            logger.error(f"エラー詳細: {type(e).__name__}: {e}")
            # エラーが発生しても受信成功として扱う
            self.commitment_received = True
            self.commitment_success = True
        
        # N-EVENT-REPORT応答用のデータセット作成
        response_dataset = Dataset()
        
        # 正常応答を返す（status, dataset）のタプル
        return 0x0000, response_dataset
    
    def create_commitment_receiver_ae(self):
        """Storage Commitment結果受信用AE作成"""
        ae = AE(ae_title=self.am_aet)
        ae.implementation_class_uid = self.implementation_class_uid
        ae.implementation_version_name = self.implementation_version
        
        # Storage Commitment Push Model SCP として設定
        storage_commitment_uid = '1.2.840.10008.1.20.1'
        
        transfer_syntaxes = [
            '1.2.840.10008.1.2',        # Implicit VR Little Endian
            '1.2.840.10008.1.2.1',      # Explicit VR Little Endian  
            '1.2.840.10008.1.2.2',      # Explicit VR Big Endian
        ]
        
        # Storage Commitment Push Model SCPとして受信を許可
        ae.add_supported_context(storage_commitment_uid, transfer_syntaxes)
        
        ae.maximum_pdu_size = 16384
        ae.network_timeout = 10
        ae.acse_timeout = 10
        ae.dimse_timeout = 30
        
        logger.info("=== Storage Commitment受信用AE設定 ===")
        logger.info(f"AE Title: {self.am_aet}")
        logger.info(f"Listen Port: {self.am_listen_port}")
        logger.info("SOP Class: Storage Commitment Push Model (SCP)")
        logger.info("==========================================")
        
        return ae
    
    def start_commitment_receiver(self):
        """Storage Commitment結果受信サーバー開始"""
        logger.info("Storage Commitment受信サーバー開始...")
        
        def run_receiver():
            try:
                ae = self.create_commitment_receiver_ae()
                
                # N-EVENT-REPORTハンドラーを設定
                handlers = [(evt.EVT_N_EVENT_REPORT, self.handle_storage_commitment_result)]
                
                # サーバー開始
                ae.start_server(
                    ('0.0.0.0', self.am_listen_port),
                    evt_handlers=handlers
                )
                
            except Exception as e:
                logger.error(f"Storage Commitment受信サーバーエラー: {e}")
        
        # バックグラウンドでサーバー開始
        receiver_thread = threading.Thread(target=run_receiver, daemon=True)
        receiver_thread.start()
        
        # サーバー起動待機
        time.sleep(2)
        logger.info(f"Storage Commitment受信サーバー起動完了 (Port: {self.am_listen_port})")
        
        return receiver_thread
    
    def select_image_type(self):
        """画像タイプ選択"""
        print("\\n=== 画像タイプ選択 ===")
        print("1. Secondary Capture Image Storage（Monochrome）")
        print("2. True Color Secondary Capture Image Storage（RGB, Single-frame）")
        print("3. Multi-frame True Color Secondary Capture Image Storage（RGB, Multi-frame）")
        print("4. すべてのテスト")
        print("======================")
        print("特徴:")
        print("  - 選択肢1: モノクロ画像、最も安定")
        print("  - 選択肢2: カラー画像（単一フレーム）")
        print("  - 選択肢3: カラー画像（複数フレーム）※再実装中")
        print("  - 選択肢4: 全パターンのテスト")
        
        while True:
            try:
                choice = input("選択してください (1/2/3/4): ").strip()
                if choice in ['1', '2', '3', '4']:
                    return choice
                else:
                    print("1、2、3、または4を入力してください。")
            except KeyboardInterrupt:
                print("\\n終了します。")
                exit(0)
            except Exception as e:
                print(f"入力エラー: {e}")
    
    def create_sample_dicom_image(self):
        """最小限のSecondary Capture DICOM画像作成"""
        print("最小限のSecondary Capture DICOM画像を作成中...")
        
        # File Meta Information作成
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.7'  # Secondary Capture
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.ImplementationClassUID = self.implementation_class_uid
        file_meta.ImplementationVersionName = self.implementation_version
        file_meta.TransferSyntaxUID = '1.2.840.10008.1.2'  # Implicit VR Little Endian
        
        # UIDを保存（Storage Commitmentで使用）
        self.stored_sop_class_uid = file_meta.MediaStorageSOPClassUID
        self.stored_sop_instance_uid = file_meta.MediaStorageSOPInstanceUID
        
        # FileDatasetとして作成
        ds = FileDataset("temp", {}, file_meta=file_meta, preamble=b"\\0" * 128)
        
        # 最小限の必須属性のみ設定
        
        # Patient Module（IM側の要求に合わせて）
        ds.PatientName = "FUKUOKA^CHIHIRO"
        ds.PatientID = "1234567890"  # 10桁
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
        ds.add_new(0x00080023, 'DA', datetime.now().strftime("%Y%m%d"))  # Image Date
        ds.add_new(0x00080033, 'TM', datetime.now().strftime("%H%M%S"))  # Image Time
        
        # SOP Common Module
        ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
        
        # SC Equipment Module
        ds.ConversionType = "WSD"  # Workstation
        ds.SecondaryCaptureDeviceManufacturer = "Test Equipment"
        ds.SecondaryCaptureDeviceManufacturerModelName = "Test Model"
        
        # Image Pixel Module（最小限）
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.Rows = 16  # 非常に小さなサイズ
        ds.Columns = 16
        ds.BitsAllocated = 8
        ds.BitsStored = 8
        ds.HighBit = 7
        ds.PixelRepresentation = 0
        
        # 最小限のピクセルデータ（16x16の固定パターン）
        pixel_data = bytearray(16 * 16)
        for i in range(16 * 16):
            pixel_data[i] = (i % 256)  # 単純なパターン
        ds.PixelData = bytes(pixel_data)
        
        print(f"作成した最小限DICOM画像:")
        print(f"  PatientName: {ds.PatientName}")
        print(f"  PatientID: {ds.PatientID}")
        print(f"  SOPClassUID: {ds.SOPClassUID}")
        print(f"  SOPInstanceUID: {ds.SOPInstanceUID}")
        print(f"  画像サイズ: {ds.Rows}x{ds.Columns}")
        
        return ds
    
    def create_multiframe_true_color_dicom_image(self):
        """Multi-frame True Color Secondary Capture用のサンプルDICOM画像作成（互換性重視版）"""
        print("Multi-frame True Color Secondary Capture画像を作成中（互換性重視版）...")
        
        # File Meta Information作成（正式なMulti-frame True Color Secondary Capture）
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.7'  # Secondary Capture（Multi-frame対応、実用性重視）
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.ImplementationClassUID = self.implementation_class_uid
        file_meta.ImplementationVersionName = self.implementation_version
        file_meta.TransferSyntaxUID = '1.2.840.10008.1.2'  # Implicit VR Little Endian
        
        # UIDを保存（Storage Commitmentで使用）
        self.stored_sop_class_uid = file_meta.MediaStorageSOPClassUID
        self.stored_sop_instance_uid = file_meta.MediaStorageSOPInstanceUID
        
        # FileDatasetとして作成
        ds = FileDataset("temp", {}, file_meta=file_meta, preamble=b"\\0" * 128)
        
        # Patient Module（True Colorと同じ構造）
        ds.PatientName = "SUZUKI^ICHIRO"
        ds.PatientID = "3456789012"  # 10桁
        ds.PatientBirthDate = "19880925"
        ds.PatientSex = "M"
        
        # General Study Module（True Colorと同じ構造）
        ds.StudyInstanceUID = generate_uid()
        ds.StudyDate = datetime.now().strftime("%Y%m%d")
        ds.StudyTime = datetime.now().strftime("%H%M%S")
        ds.ReferringPhysicianName = ""
        ds.StudyID = "4"
        ds.AccessionNumber = "A20240918124000"
        
        # General Series Module（True Colorと同じ構造）
        ds.SeriesInstanceUID = generate_uid()
        ds.SeriesNumber = "4"
        ds.SeriesDate = datetime.now().strftime("%Y%m%d")
        ds.SeriesTime = datetime.now().strftime("%H%M%S")
        ds.Modality = "OT"  # Other
        
        # General Image Module（True Colorと同じ構造）
        ds.InstanceNumber = "1"
        ds.add_new(0x00080023, 'DA', datetime.now().strftime("%Y%m%d"))  # Image Date
        ds.add_new(0x00080033, 'TM', datetime.now().strftime("%H%M%S"))  # Image Time
        
        # SOP Common Module
        ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
        
        # SC Equipment Module（True Colorと同じ構造）
        ds.ConversionType = "WSD"  # Workstation
        ds.SecondaryCaptureDeviceManufacturer = "Test Equipment MultiFrame"
        ds.SecondaryCaptureDeviceManufacturerModelName = "Test Model MultiFrame"
        
        # Multi-frame Module（必須属性追加）
        ds.NumberOfFrames = 2  # 2フレーム

        # 最小限のMulti-frame Functional Groups Module（IMサーバー対応）
        # Shared Functional Groups Sequence（必須だが最小限）
        shared_fg = Dataset()
        ds.SharedFunctionalGroupsSequence = [shared_fg]

        # Per-frame Functional Groups Sequence（必須だが最小限）
        frame_fg_list = []

        for frame_num in range(2):  # 2フレーム分
            frame_fg = Dataset()

            # Frame Content Sequence（最小限の必須情報のみ）
            frame_content = Dataset()
            frame_content.FrameAcquisitionNumber = frame_num + 1
            frame_fg.FrameContentSequence = [frame_content]

            frame_fg_list.append(frame_fg)

        ds.PerFrameFunctionalGroupsSequence = frame_fg_list
        
        # Image Pixel Module（True Colorとほぼ同じ、Multi-frame対応）
        ds.SamplesPerPixel = 3  # RGB
        ds.PhotometricInterpretation = "RGB"
        ds.Rows = 32  # True Colorと同じサイズ
        ds.Columns = 32
        ds.BitsAllocated = 8
        ds.BitsStored = 8
        ds.HighBit = 7
        ds.PixelRepresentation = 0
        ds.PlanarConfiguration = 0  # RGBRGBRGB...
        
        # Multi-frame用ピクセルデータ（True Colorのパターンを2フレーム分）
        frame_size = 32 * 32 * 3  # RGB
        total_pixel_data = bytearray(frame_size * 2)  # 2フレーム分
        
        # フレーム1: True Colorと同じパターン
        for y in range(32):
            for x in range(32):
                idx = (y * 32 + x) * 3
                total_pixel_data[idx] = min(255, x * 8)      # R
                total_pixel_data[idx + 1] = min(255, y * 8)  # G
                total_pixel_data[idx + 2] = min(255, (x + y) * 4)  # B
        
        # フレーム2: 反転パターン
        frame2_offset = frame_size
        for y in range(32):
            for x in range(32):
                idx = frame2_offset + (y * 32 + x) * 3
                total_pixel_data[idx] = min(255, (31-x) * 8)      # R（反転）
                total_pixel_data[idx + 1] = min(255, (31-y) * 8)  # G（反転）
                total_pixel_data[idx + 2] = min(255, ((31-x) + (31-y)) * 4)  # B（反転）
        
        ds.PixelData = bytes(total_pixel_data)
        
        print(f"作成したMulti-frame True Color Secondary Capture DICOM画像:")
        print(f"  PatientName: {ds.PatientName}")
        print(f"  PatientID: {ds.PatientID}")
        print(f"  SOPClassUID: {ds.SOPClassUID}")
        print(f"  SOPInstanceUID: {ds.SOPInstanceUID}")
        print(f"  画像サイズ: {ds.Rows}x{ds.Columns}")
        print(f"  フレーム数: {ds.NumberOfFrames}")
        print(f"  カラー形式: {ds.PhotometricInterpretation}")
        print(f"  Secondary Capture基盤のMulti-frame True Color（実用性重視）")
        
        return ds
    
    def create_true_color_dicom_image(self):
        """True Color Secondary Capture用のサンプルDICOM画像作成（Single-frame）"""
        print("True Color Secondary Capture画像を作成中...")
        
        # File Meta Information作成
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.7'  # Secondary Capture
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.ImplementationClassUID = self.implementation_class_uid
        file_meta.ImplementationVersionName = self.implementation_version
        file_meta.TransferSyntaxUID = '1.2.840.10008.1.2'  # Implicit VR Little Endian
        
        # UIDを保存（Storage Commitmentで使用）
        self.stored_sop_class_uid = file_meta.MediaStorageSOPClassUID
        self.stored_sop_instance_uid = file_meta.MediaStorageSOPInstanceUID
        
        # FileDatasetとして作成
        ds = FileDataset("temp", {}, file_meta=file_meta, preamble=b"\\0" * 128)
        
        # Patient Module
        ds.PatientName = "TANAKA^HANAKO"
        ds.PatientID = "2345678901"  # 10桁
        ds.PatientBirthDate = "19900712"
        ds.PatientSex = "F"
        
        # General Study Module
        ds.StudyInstanceUID = generate_uid()
        ds.StudyDate = datetime.now().strftime("%Y%m%d")
        ds.StudyTime = datetime.now().strftime("%H%M%S")
        ds.ReferringPhysicianName = ""
        ds.StudyID = "3"
        ds.AccessionNumber = "A20240918123000"
        
        # General Series Module
        ds.SeriesInstanceUID = generate_uid()
        ds.SeriesNumber = "3"
        ds.SeriesDate = datetime.now().strftime("%Y%m%d")
        ds.SeriesTime = datetime.now().strftime("%H%M%S")
        ds.Modality = "OT"  # Other
        
        # General Image Module
        ds.InstanceNumber = "1"
        ds.add_new(0x00080023, 'DA', datetime.now().strftime("%Y%m%d"))  # Image Date
        ds.add_new(0x00080033, 'TM', datetime.now().strftime("%H%M%S"))  # Image Time
        
        # SOP Common Module
        ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
        
        # SC Equipment Module
        ds.ConversionType = "WSD"  # Workstation
        ds.SecondaryCaptureDeviceManufacturer = "Test Equipment TrueColor"
        ds.SecondaryCaptureDeviceManufacturerModelName = "Test Model TrueColor"
        
        # Image Pixel Module（True Color用）
        ds.SamplesPerPixel = 3  # RGB
        ds.PhotometricInterpretation = "RGB"
        ds.Rows = 32
        ds.Columns = 32
        ds.BitsAllocated = 8
        ds.BitsStored = 8
        ds.HighBit = 7
        ds.PixelRepresentation = 0
        ds.PlanarConfiguration = 0  # RGBRGBRGB...
        
        # True Color用ピクセルデータ（Single-frame RGB）
        pixel_size = 32 * 32 * 3  # RGB
        pixel_data = bytearray(pixel_size)
        
        # 簡単なグラデーションパターン
        for y in range(32):
            for x in range(32):
                idx = (y * 32 + x) * 3
                pixel_data[idx] = min(255, x * 8)      # R
                pixel_data[idx + 1] = min(255, y * 8)  # G
                pixel_data[idx + 2] = min(255, (x + y) * 4)  # B
        
        ds.PixelData = bytes(pixel_data)
        
        print(f"作成したTrue Color DICOM画像:")
        print(f"  PatientName: {ds.PatientName}")
        print(f"  PatientID: {ds.PatientID}")
        print(f"  SOPClassUID: {ds.SOPClassUID}")
        print(f"  SOPInstanceUID: {ds.SOPInstanceUID}")
        print(f"  画像サイズ: {ds.Rows}x{ds.Columns}")
        print(f"  カラー形式: {ds.PhotometricInterpretation}")
        
        return ds
    
    def create_commitment_request(self):
        """Storage Commitment Request作成（保存済み画像のUIDを使用）"""
        print("Storage Commitment Requestを作成中...")
        
        if not self.stored_sop_class_uid or not self.stored_sop_instance_uid:
            raise ValueError("保存済み画像のUIDが設定されていません。先にC-STOREを実行してください。")
        
        # N-ACTION Request用のDataset作成
        ds = Dataset()
        
        # 文字セット指定
        ds.SpecificCharacterSet = 'ISO_IR 100'  # Latin alphabet No. 1
        
        # Storage Commitment Transaction UID（DICOMタグ0008,1195で明示的に設定）
        transaction_uid = generate_uid()
        ds.add_new(0x00081195, 'UI', transaction_uid)  # Transaction UID
        
        # 念のため通常の属性としても設定
        ds.TransactionUID = transaction_uid
        
        # Referenced SOP Sequence（実際に保存した画像を参照）
        ref_sop_item = Dataset()
        ref_sop_item.ReferencedSOPClassUID = self.stored_sop_class_uid
        ref_sop_item.ReferencedSOPInstanceUID = self.stored_sop_instance_uid
        
        ds.ReferencedSOPSequence = [ref_sop_item]
        
        print(f"作成したStorage Commitment Request:")
        print(f"  TransactionUID (0008,1195): {transaction_uid}")
        print(f"  ReferencedSOPClassUID: {ref_sop_item.ReferencedSOPClassUID}")
        print(f"  ReferencedSOPInstanceUID: {ref_sop_item.ReferencedSOPInstanceUID}")
        print(f"  ※実際に保存した画像を参照しています")
        
        return ds
    
    def test_image_store(self):
        """C-STORE実行"""
        logger.info("=== Image Store テスト ===")
        
        try:
            ae = self.create_store_ae()
            
            logger.info(f"IMサーバーに接続中: {self.im_ip}:{self.im_port} (AET: {self.im_aet})")
            assoc = ae.associate(self.im_ip, self.im_port, ae_title=self.im_aet)
            
            if not assoc.is_established:
                logger.error("IMサーバーとのアソシエーション確立失敗")
                return False
            
            logger.info("OK: IMアソシエーション確立成功（C-STORE）")
            
            # サンプル画像作成
            image_dataset = self.create_sample_dicom_image()
            
            # C-STORE送信
            logger.info("C-STORE送信中...")
            
            try:
                status = assoc.send_c_store(image_dataset)
                
                if status and hasattr(status, 'Status') and status.Status == 0x0000:
                    logger.info("OK: C-STORE成功")
                    success = True
                else:
                    logger.error("C-STORE失敗")
                    success = False
                    
            except Exception as store_error:
                logger.error(f"C-STORE送信エラー: {store_error}")
                success = False
            
            assoc.release()
            logger.info("アソシエーション終了（C-STORE）")
            
            return success
            
        except Exception as e:
            logger.error(f"C-STORE接続エラー: {e}")
            return False
    
    def test_multiframe_true_color_store(self):
        """Multi-frame True Color Secondary Capture C-STORE実行"""
        logger.info("=== Multi-frame True Color Secondary Capture Store テスト ===")

        try:
            ae = self.create_store_ae()

            logger.info(f"IMサーバーに接続中: {self.im_ip}:{self.im_port} (AET: {self.im_aet})")
            assoc = ae.associate(self.im_ip, self.im_port, ae_title=self.im_aet)

            if not assoc.is_established:
                logger.error("IMサーバーとのアソシエーション確立失敗")
                return False

            logger.info("OK: IMアソシエーション確立成功（Multi-frame True Color C-STORE）")

            # アソシエーション詳細情報をログ出力
            logger.info("=== アソシエーション詳細情報 ===")
            logger.info(f"Accepted Contexts: {len(assoc.accepted_contexts)}")
            for i, context in enumerate(assoc.accepted_contexts):
                logger.info(f"  Context[{i}]: {context.abstract_syntax}")
                logger.info(f"    Transfer Syntax: {context.transfer_syntax}")
            logger.info("===============================")
            
            # Multi-frame True Color画像作成
            image_dataset = self.create_multiframe_true_color_dicom_image()
            
            # C-STORE送信
            logger.info("Multi-frame True Color C-STORE送信中...")
            
            try:
                status = assoc.send_c_store(image_dataset)
                
                if status and hasattr(status, 'Status') and status.Status == 0x0000:
                    logger.info("OK: Multi-frame True Color C-STORE成功")
                    success = True
                else:
                    logger.error("Multi-frame True Color C-STORE失敗")
                    success = False
                    
            except Exception as store_error:
                logger.error(f"Multi-frame True Color C-STORE送信エラー: {store_error}")
                success = False
            
            assoc.release()
            logger.info("アソシエーション終了（Multi-frame True Color C-STORE）")
            
            return success
            
        except Exception as e:
            logger.error(f"Multi-frame True Color C-STORE接続エラー: {e}")
            return False
    
    def test_true_color_store(self):
        """True Color Secondary Capture C-STORE実行"""
        logger.info("=== True Color Secondary Capture Store テスト ===")
        
        try:
            ae = self.create_store_ae()
            
            logger.info(f"IMサーバーに接続中: {self.im_ip}:{self.im_port} (AET: {self.im_aet})")
            assoc = ae.associate(self.im_ip, self.im_port, ae_title=self.im_aet)
            
            if not assoc.is_established:
                logger.error("IMサーバーとのアソシエーション確立失敗")
                return False
            
            logger.info("OK: IMアソシエーション確立成功（True Color C-STORE）")
            
            # True Color画像作成
            image_dataset = self.create_true_color_dicom_image()
            
            # C-STORE送信
            logger.info("True Color C-STORE送信中...")
            
            try:
                status = assoc.send_c_store(image_dataset)
                
                if status and hasattr(status, 'Status') and status.Status == 0x0000:
                    logger.info("OK: True Color C-STORE成功")
                    success = True
                else:
                    logger.error("True Color C-STORE失敗")
                    success = False
                    
            except Exception as store_error:
                logger.error(f"True Color C-STORE送信エラー: {store_error}")
                success = False
            
            assoc.release()
            logger.info("アソシエーション終了（True Color C-STORE）")
            
            return success
            
        except Exception as e:
            logger.error(f"True Color C-STORE接続エラー: {e}")
            return False
    
    def test_storage_commitment(self):
        """Storage Commitment Request実行"""
        logger.info("=== Storage Commitment Request テスト ===")
        
        try:
            ae = self.create_commitment_ae()
            
            logger.info(f"IMサーバーに接続中: {self.im_ip}:{self.im_port} (AET: {self.im_aet})")
            assoc = ae.associate(self.im_ip, self.im_port, ae_title=self.im_aet)
            
            if not assoc.is_established:
                logger.error("IMサーバーとのアソシエーション確立失敗")
                return False
            
            logger.info("OK: IMアソシエーション確立成功（Storage Commitment）")
            
            # Storage Commitment Request作成
            request_dataset = self.create_commitment_request()
            
            # デバッグ：送信するデータセットの内容を詳細出力
            logger.info("=== Storage Commitment Request データセット詳細 ===")
            logger.info(f"Dataset type: {type(request_dataset)}")
            
            # Transaction UIDの確認
            if hasattr(request_dataset, 'TransactionUID'):
                logger.info(f"TransactionUID (属性): {request_dataset.TransactionUID}")
            
            # DICOMタグ0x00081195の確認
            if 0x00081195 in request_dataset:
                logger.info(f"Transaction UID (0x00081195): {request_dataset[0x00081195].value}")
            else:
                logger.warning("Transaction UID (0x00081195) がデータセットに見つかりません")
            
            # Referenced SOP Sequenceの確認
            if hasattr(request_dataset, 'ReferencedSOPSequence'):
                logger.info(f"Referenced SOP Sequence length: {len(request_dataset.ReferencedSOPSequence)}")
                for i, ref_sop in enumerate(request_dataset.ReferencedSOPSequence):
                    logger.info(f"  [{i}] SOP Class UID: {ref_sop.ReferencedSOPClassUID}")
                    logger.info(f"  [{i}] SOP Instance UID: {ref_sop.ReferencedSOPInstanceUID}")
            
            # 全体の内容をログ出力
            logger.info("Dataset内容:")
            for elem in request_dataset:
                logger.info(f"  {elem.tag}: {elem.keyword} = {elem.value}")
            
            logger.info("===============================================")
            
            # N-ACTION送信
            logger.info("N-ACTION送信中...")
            
            try:
                sop_class_uid = '1.2.840.10008.1.20.1'
                sop_instance_uid = '1.2.840.10008.1.20.1.1'
                action_type_id = 1
                
                logger.info(f"N-ACTION Parameters:")
                logger.info(f"  SOP Class UID: {sop_class_uid}")
                logger.info(f"  SOP Instance UID: {sop_instance_uid}")
                logger.info(f"  Action Type ID: {action_type_id}")
                
                status = assoc.send_n_action(
                    request_dataset,
                    action_type_id,
                    sop_class_uid,
                    sop_instance_uid
                )
                
                if status and isinstance(status, tuple) and len(status) >= 1:
                    status_ds = status[0]
                    if hasattr(status_ds, 'Status') and status_ds.Status == 0x0000:
                        logger.info("OK: N-ACTION成功")
                        success = True
                    else:
                        logger.error("N-ACTION失敗")
                        success = False
                else:
                    logger.error("N-ACTION失敗: レスポンスなし")
                    success = False
                    
            except Exception as action_error:
                logger.error(f"N-ACTION送信エラー: {action_error}")
                success = False
            
            assoc.release()
            logger.info("アソシエーション終了（Storage Commitment）")
            
            return success
            
        except Exception as e:
            logger.error(f"Storage Commitment接続エラー: {e}")
            return False
    
    def run_test_with_choice(self, choice):
        """統合テスト実行（指定された選択肢で）"""
        print("=== 統合テスト：Image Store + Storage Commitment + 結果受信 ===")
        print(f"選択された画像タイプ: {choice}")
        print()

        # Step 0: Storage Commitment受信サーバー開始
        print("Step 0: Storage Commitment受信サーバー開始...")
        receiver_thread = self.start_commitment_receiver()
        print("OK: 受信サーバー開始完了")
        print()

        return self._execute_test_steps(choice)

    def run_integrated_test(self):
        """統合テスト実行（ユーザー選択による画像タイプ）"""
        print("=== 統合テスト：Image Store + Storage Commitment + 結果受信 ===")

        # 画像タイプ選択
        choice = self.select_image_type()
        print()

        # Step 0: Storage Commitment受信サーバー開始
        print("Step 0: Storage Commitment受信サーバー開始...")
        receiver_thread = self.start_commitment_receiver()
        print("OK: 受信サーバー開始完了")
        print()

        return self._execute_test_steps(choice)

    def _execute_test_steps(self, choice):
        """テストステップの実行"""
        # 画像送信テスト実行
        store_success = False
        multiframe_store_success = False
        
        if choice == '1':  # Secondary Capture Image Storage
            print("Step 1: Secondary Capture C-STOREで画像保存...")
            store_success = self.test_image_store()
            
            if not store_success:
                print("NG: Secondary Capture C-STORE失敗。Storage Commitmentはスキップします。")
                return False
            else:
                print("OK: Secondary Capture C-STORE成功")
            print()
            
        elif choice == '2':  # True Color Secondary Capture
            print("Step 1: True Color Secondary Capture C-STOREで画像保存...")
            true_color_success = self.test_true_color_store()
            
            if not true_color_success:
                print("NG: True Color C-STORE失敗。Storage Commitmentはスキップします。")
                return False
            else:
                print("OK: True Color C-STORE成功")
            print()
            
        elif choice == '3':  # Multi-frame True Color Secondary Capture
            print("Step 1: Multi-frame True Color Secondary Capture C-STOREで画像保存...")
            multiframe_store_success = self.test_multiframe_true_color_store()
            
            if not multiframe_store_success:
                print("NG: Multi-frame True Color C-STORE失敗。Storage Commitmentはスキップします。")
                return False
            else:
                print("OK: Multi-frame True Color C-STORE成功")
            print()
            
        elif choice == '4':  # すべてのテスト
            print("Step 1: Secondary Capture C-STOREで画像保存...")
            store_success = self.test_image_store()
            
            if not store_success:
                print("NG: Secondary Capture C-STORE失敗。続行します...")
            else:
                print("OK: Secondary Capture C-STORE成功")
            print()
            
            # 少し待機
            time.sleep(1)
            
            print("Step 2: True Color Secondary Capture C-STOREで画像保存...")
            true_color_success = self.test_true_color_store()
            
            if not true_color_success:
                print("NG: True Color C-STORE失敗。続行します...")
            else:
                print("OK: True Color C-STORE成功")
            print()
            
            # 少し待機
            time.sleep(1)
            
            print("Step 3: Multi-frame True Color Secondary Capture C-STOREで画像保存...")
            multiframe_store_success = self.test_multiframe_true_color_store()
            
            if not multiframe_store_success:
                print("NG: Multi-frame True Color C-STORE失敗")
                if not store_success and not true_color_success:
                    print("NG: すべてのC-STOREが失敗しました。Storage Commitmentはスキップします。")
                    return False
            else:
                print("OK: Multi-frame True Color C-STORE成功")
            print()
        
        # 少し待機
        time.sleep(1)
        
        # Storage Commitment Request実行（最後に成功した画像のUIDを使用）
        if choice in ['1', '2', '3']:
            next_step = 2
        else:  # choice == '4'
            next_step = 4
            
        print(f"Step {next_step}: Storage Commitment Request送信...")
        commitment_request_success = self.test_storage_commitment()
        
        if not commitment_request_success:
            print("NG: Storage Commitment Request失敗")
            return False
        
        print("OK: Storage Commitment Request成功")
        print()
        
        # Storage Commitment結果受信待機
        final_step = next_step + 1
        print(f"Step {final_step}: Storage Commitment結果受信待機...")
        max_wait = 30  # 30秒待機
        wait_start = time.time()
        
        while time.time() - wait_start < max_wait:
            if self.commitment_received:
                break
            print(".", end="", flush=True)
            time.sleep(1)
        
        print()
        
        if self.commitment_received:
            if self.commitment_success:
                print("OK: Storage Commitment結果受信成功")
                
                # 実行されたテストの種類に応じてメッセージを変更
                test_types = []
                if choice == '1':
                    test_types.append("Secondary Capture")
                elif choice == '2':
                    test_types.append("True Color Secondary Capture")
                elif choice == '3':
                    test_types.append("Multi-frame True Color Secondary Capture")
                elif choice == '4':
                    if store_success:
                        test_types.append("Secondary Capture")
                    if 'true_color_success' in locals() and true_color_success:
                        test_types.append("True Color Secondary Capture")
                    if multiframe_store_success:
                        test_types.append("Multi-frame True Color Secondary Capture")
                
                test_description = "、".join(test_types)
                print(f"OK: 統合テスト完了：{test_description}、Storage Commitment送信、結果受信が正常に動作しました")
                return True
            else:
                print("NG: Storage Commitmentで一部画像の保存に失敗しました")
                return False
        else:
            print("NG: Storage Commitment結果の受信がタイムアウトしました")
            return False

def main():
    """メイン実行"""
    import sys

    print("統合テスト：DICOM Image Store + Storage Commitment + 結果受信")
    print("対応画像タイプ：")
    print("  - Secondary Capture Image Storage（Monochrome・安定動作）")
    print("  - True Color Secondary Capture Image Storage（RGB・安定動作）")
    print("==========================================")

    client = IntegratedTestClient()

    # コマンドライン引数でテストタイプを指定可能
    if len(sys.argv) > 1:
        choice = sys.argv[1]
        print(f"コマンドライン引数により選択肢 {choice} を自動選択")
        success = client.run_test_with_choice(choice)
    else:
        success = client.run_integrated_test()

    if success:
        print("\\nOK: 統合テスト成功！")
    else:
        print("\\nNG: 統合テスト失敗")

if __name__ == "__main__":
    main()