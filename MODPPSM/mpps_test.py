#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MPPS統合テスト：Modality Performed Procedure Step
1. N-CREATE（検査開始）でMPPSインスタンスを作成
2. N-SET（検査終了）でMPPSインスタンスを更新
"""

import logging
import time
from datetime import datetime
from pynetdicom import AE, evt
from pydicom.dataset import Dataset
from pydicom.uid import generate_uid

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MPPSTestClient:
    """MPPS統合テストクライアント"""

    def __init__(self):
        # AM (MOD) の設定 - 既存の成功例に合わせる
        self.am_aet = "LTMONITOR"
        # PPSM サーバーの設定
        self.ppsm_aet = "PPSM"
        self.ppsm_ip = "127.0.0.1"
        self.ppsm_port = 11115

        # Implementation情報
        self.implementation_class_uid = "1.2.392.200036.8120.101.9"
        self.implementation_version = "Monocube1.0.0.0"

        # MPPS Instance UID（検査開始で作成、検査終了で更新）
        self.mpps_sop_instance_uid = None

        # 検査情報
        self.study_instance_uid = None
        self.performed_procedure_step_start_date = None
        self.performed_procedure_step_start_time = None

    def create_mpps_ae(self):
        """MPPS用AE作成"""
        ae = AE(ae_title=self.am_aet)
        ae.implementation_class_uid = self.implementation_class_uid
        ae.implementation_version_name = self.implementation_version

        # Modality Performed Procedure Step SOP Class
        mpps_uid = '1.2.840.10008.3.1.2.3.3'  # Modality Performed Procedure Step SOP Class

        transfer_syntaxes = [
            '1.2.840.10008.1.2',        # Implicit VR Little Endian
            '1.2.840.10008.1.2.1',      # Explicit VR Little Endian
            '1.2.840.10008.1.2.2',      # Explicit VR Big Endian
        ]

        ae.add_requested_context(mpps_uid, transfer_syntaxes)

        ae.maximum_pdu_size = 16384
        ae.network_timeout = 10
        ae.acse_timeout = 10
        ae.dimse_timeout = 30

        return ae

    def create_mpps_in_progress_dataset(self):
        """検査開始（IN PROGRESS）のMPPSデータセット作成"""
        logger.info("検査開始（IN PROGRESS）MPPSデータセット作成中...")

        # 新しいMPPS SOP Instance UID生成
        self.mpps_sop_instance_uid = generate_uid()

        # 検査情報生成
        self.study_instance_uid = generate_uid()
        self.performed_procedure_step_start_date = datetime.now().strftime("%Y%m%d")
        self.performed_procedure_step_start_time = datetime.now().strftime("%H%M%S")

        ds = Dataset()

        # SOP Common Module
        ds.SOPClassUID = '1.2.840.10008.3.1.2.3.3'  # Modality Performed Procedure Step SOP Class
        ds.SOPInstanceUID = self.mpps_sop_instance_uid

        # Performed Procedure Step Information Module
        ds.PerformedProcedureStepID = "PPS001"
        ds.PerformedStationAETitle = self.am_aet
        ds.PerformedStationName = "MOD_Station_01"
        ds.PerformedLocation = "Room_A"
        ds.PerformedProcedureStepStartDate = self.performed_procedure_step_start_date
        ds.PerformedProcedureStepStartTime = self.performed_procedure_step_start_time
        ds.PerformedProcedureStepStatus = "IN PROGRESS"
        ds.PerformedProcedureStepDescription = "Connect-a-thon Test Procedure"
        ds.PerformedProcedureTypeDescription = "Test Modality Procedure"
        ds.Modality = "OT"  # Other

        # 必須: Procedure Code Sequence (0008,1032)
        procedure_code = Dataset()
        procedure_code.CodeValue = "P1-12345"
        procedure_code.CodingSchemeDesignator = "99_IMOS"
        procedure_code.CodeMeaning = "Test Procedure Code"
        ds.add_new(0x00081032, 'SQ', [procedure_code])  # Procedure Code Sequence

        # 必須: Performed Protocol Code Sequence (0040,0260)
        performed_protocol_code = Dataset()
        performed_protocol_code.CodeValue = "PROT-001"
        performed_protocol_code.CodingSchemeDesignator = "99_IMOS"
        performed_protocol_code.CodeMeaning = "Standard Test Protocol"
        ds.add_new(0x00400260, 'SQ', [performed_protocol_code])  # Performed Protocol Code Sequence

        # Required tags (0040,0254) and (0040,0255)
        ds.add_new(0x00400254, 'LO', "Test Procedure Step Description")  # Performed Procedure Step Description
        ds.add_new(0x00400255, 'LO', "Test Procedure Type Description")  # Performed Procedure Type Description

        # Performed Procedure Step Relationship Module
        ds.PatientName = "YAMADA^TARO"
        ds.PatientID = "9876543210"  # 10桁
        ds.PatientBirthDate = "19850315"
        ds.PatientSex = "M"

        # Study関連
        ds.StudyInstanceUID = self.study_instance_uid
        ds.StudyID = "ST001"
        ds.AccessionNumber = "ACC20250918001"

        # Requested Procedure Module（標準的な属性名を使用）
        requested_procedure = Dataset()
        requested_procedure.RequestedProcedureID = "REQ001"
        requested_procedure.RequestedProcedureDescription = "Test Requested Procedure"
        ds.add_new(0x00321060, 'SQ', [requested_procedure])  # Requested Procedure Sequence

        # Scheduled Step Attributes Sequence（標準的な属性名を使用）
        scheduled_step = Dataset()
        scheduled_step.ScheduledStationAETitle = self.am_aet
        scheduled_step.ScheduledProcedureStepID = "SPS001"
        scheduled_step.ScheduledStationName = "MOD_Station_01"
        scheduled_step.ScheduledProcedureStepLocation = "Room_A"

        # Procedure Code Sequence
        procedure_code = Dataset()
        procedure_code.CodeValue = "P1-12345"
        procedure_code.CodingSchemeDesignator = "99_IMOS"
        procedure_code.CodeMeaning = "Test Procedure"
        scheduled_step.add_new(0x00081032, 'SQ', [procedure_code])  # Procedure Code Sequence

        ds.add_new(0x00400270, 'SQ', [scheduled_step])  # Scheduled Step Attributes Sequence

        # 空のPerformed Series Sequence（検査開始時）
        ds.PerformedSeriesSequence = []

        logger.info(f"検査開始MPPSデータセット作成完了:")
        logger.info(f"  MPPS SOP Instance UID: {self.mpps_sop_instance_uid}")
        logger.info(f"  Study Instance UID: {self.study_instance_uid}")
        logger.info(f"  Patient Name: {ds.PatientName}")
        logger.info(f"  Status: {ds.PerformedProcedureStepStatus}")

        return ds

    def create_mpps_completed_dataset(self):
        """検査終了（COMPLETED）のMPPSデータセット作成"""
        logger.info("検査終了（COMPLETED）MPPSデータセット作成中...")

        if not self.mpps_sop_instance_uid:
            raise ValueError("MPPS SOP Instance UIDが設定されていません。先に検査開始を実行してください。")

        ds = Dataset()

        # SOP Common Module
        ds.SOPClassUID = '1.2.840.10008.3.1.2.3.3'  # Modality Performed Procedure Step SOP Class
        ds.SOPInstanceUID = self.mpps_sop_instance_uid

        # 検査終了時の更新情報
        performed_procedure_step_end_date = datetime.now().strftime("%Y%m%d")
        performed_procedure_step_end_time = datetime.now().strftime("%H%M%S")

        ds.PerformedProcedureStepEndDate = performed_procedure_step_end_date
        ds.PerformedProcedureStepEndTime = performed_procedure_step_end_time
        ds.PerformedProcedureStepStatus = "COMPLETED"

        # 必須: Procedure Code Sequence (0008,1032) - 検査終了時も必要
        procedure_code = Dataset()
        procedure_code.CodeValue = "P1-12345"
        procedure_code.CodingSchemeDesignator = "99_IMOS"
        procedure_code.CodeMeaning = "Test Procedure Code"
        ds.add_new(0x00081032, 'SQ', [procedure_code])

        # 必須: Performed Protocol Code Sequence (0040,0260) - 検査終了時も必要
        performed_protocol_code = Dataset()
        performed_protocol_code.CodeValue = "PROT-001"
        performed_protocol_code.CodingSchemeDesignator = "99_IMOS"
        performed_protocol_code.CodeMeaning = "Standard Test Protocol"
        ds.add_new(0x00400260, 'SQ', [performed_protocol_code])

        # Required tags (0040,0254) and (0040,0255) - 検査終了時も必要
        ds.add_new(0x00400254, 'LO', "Test Procedure Step Description")  # Performed Procedure Step Description
        ds.add_new(0x00400255, 'LO', "Test Procedure Type Description")  # Performed Procedure Type Description

        # Performed Series Sequence（検査で生成された画像シリーズ情報）
        performed_series = Dataset()
        performed_series.SeriesInstanceUID = generate_uid()
        performed_series.SeriesDescription = "Connect-a-thon Test Series"
        performed_series.PerformingPhysicianName = "Dr. CONNECT"
        performed_series.OperatorName = "OPERATOR_01"
        performed_series.ProtocolName = "Standard Test Protocol"
        performed_series.Modality = "OT"  # Modalityも追加
        performed_series.SeriesDate = datetime.now().strftime("%Y%m%d")
        performed_series.SeriesTime = datetime.now().strftime("%H%M%S")

        # Referenced Image Sequence（生成された画像への参照）
        referenced_image = Dataset()
        referenced_image.ReferencedSOPClassUID = "1.2.840.10008.5.1.4.1.1.7"  # Secondary Capture
        referenced_image.ReferencedSOPInstanceUID = generate_uid()
        performed_series.ReferencedImageSequence = [referenced_image]

        # Retrieved Non-Image SOP Instance Sequence（空で設定）
        performed_series.ReferencedNonImageCompositeSOPInstanceSequence = []

        ds.PerformedSeriesSequence = [performed_series]

        logger.info(f"検査終了MPPSデータセット作成完了:")
        logger.info(f"  MPPS SOP Instance UID: {self.mpps_sop_instance_uid}")
        logger.info(f"  Status: {ds.PerformedProcedureStepStatus}")
        logger.info(f"  End Date: {performed_procedure_step_end_date}")
        logger.info(f"  End Time: {performed_procedure_step_end_time}")
        logger.info(f"  Generated Series: {len(ds.PerformedSeriesSequence)}")

        return ds

    def test_mpps_in_progress(self):
        """検査開始（N-CREATE）テスト"""
        logger.info("=== MPPS検査開始（N-CREATE）テスト ===")

        try:
            ae = self.create_mpps_ae()

            # デバッグ情報出力
            logger.info("=== MPPS AE設定情報 ===")
            logger.info(f"自分のAE Title: {self.am_aet}")
            logger.info(f"接続先AE Title: {self.ppsm_aet}")
            logger.info(f"接続先IP: {self.ppsm_ip}")
            logger.info(f"接続先ポート: {self.ppsm_port}")
            logger.info(f"実装クラスUID: {self.implementation_class_uid}")
            logger.info(f"実装バージョン: {self.implementation_version}")
            logger.info("========================")

            logger.info(f"PPSMサーバーに接続中: {self.ppsm_ip}:{self.ppsm_port} (AET: {self.ppsm_aet})")
            assoc = ae.associate(self.ppsm_ip, self.ppsm_port, ae_title=self.ppsm_aet)

            if not assoc.is_established:
                logger.error("PPSMサーバーとのアソシエーション確立失敗")
                logger.error(f"アソシエーション詳細:")
                logger.error(f"  Is established: {assoc.is_established}")
                logger.error(f"  Is released: {assoc.is_released}")
                logger.error(f"  Is aborted: {assoc.is_aborted}")
                return False

            logger.info("OK: PPSMアソシエーション確立成功（N-CREATE）")

            # アソシエーション詳細情報
            logger.info("=== アソシエーション詳細情報 ===")
            logger.info(f"Accepted Contexts: {len(assoc.accepted_contexts)}")
            for i, context in enumerate(assoc.accepted_contexts):
                logger.info(f"  Context[{i}]: {context.abstract_syntax}")
                logger.info(f"    Transfer Syntax: {context.transfer_syntax}")
            logger.info("===============================")

            # MPPS IN PROGRESSデータセット作成
            mpps_dataset = self.create_mpps_in_progress_dataset()

            # N-CREATE送信
            logger.info("N-CREATE（検査開始）送信中...")

            try:
                status = assoc.send_n_create(
                    mpps_dataset,
                    '1.2.840.10008.3.1.2.3.3',  # MPPS SOP Class UID
                    self.mpps_sop_instance_uid
                )

                logger.info(f"N-CREATE レスポンス詳細:")
                logger.info(f"  Status: {status}")
                logger.info(f"  Type: {type(status)}")

                if status:
                    # pynetdicomのN-CREATEはtupleで返される: (status_dataset, dataset)
                    if isinstance(status, tuple) and len(status) >= 1:
                        status_ds = status[0]
                        logger.info(f"  Status Dataset: {status_ds}")
                        logger.info(f"  Status Dataset Type: {type(status_ds)}")

                        if hasattr(status_ds, 'Status'):
                            logger.info(f"  Status Code: 0x{status_ds.Status:04X}")
                            if status_ds.Status == 0x0000:
                                logger.info("OK: N-CREATE（検査開始）成功")
                                success = True
                            else:
                                logger.error(f"N-CREATE失敗: Status = 0x{status_ds.Status:04X}")
                                success = False
                        else:
                            # Status属性が直接見つからない場合、データセット内を検索
                            if hasattr(status_ds, 'keys') and (0x0000, 0x0900) in status_ds:
                                status_code = status_ds[0x0000, 0x0900].value
                                logger.info(f"  Status Code (from dataset): 0x{status_code:04X}")
                                if status_code == 0x0000:
                                    logger.info("OK: N-CREATE（検査開始）成功")
                                    success = True
                                else:
                                    logger.error(f"N-CREATE失敗: Status = 0x{status_code:04X}")
                                    success = False
                            else:
                                logger.error("N-CREATE失敗: Statusコードが見つかりません")
                                success = False
                    else:
                        logger.error("N-CREATE失敗: 期待されるtupleレスポンスではありません")
                        success = False
                else:
                    logger.error("N-CREATE失敗: レスポンスなし")
                    success = False

            except Exception as create_error:
                logger.error(f"N-CREATE送信エラー: {create_error}")
                success = False

            assoc.release()
            logger.info("アソシエーション終了（N-CREATE）")

            return success

        except Exception as e:
            logger.error(f"N-CREATE接続エラー: {e}")
            return False

    def test_mpps_completed(self):
        """検査終了（N-SET）テスト"""
        logger.info("=== MPPS検査終了（N-SET）テスト ===")

        try:
            ae = self.create_mpps_ae()

            logger.info(f"PPSMサーバーに接続中: {self.ppsm_ip}:{self.ppsm_port} (AET: {self.ppsm_aet})")
            assoc = ae.associate(self.ppsm_ip, self.ppsm_port, ae_title=self.ppsm_aet)

            if not assoc.is_established:
                logger.error("PPSMサーバーとのアソシエーション確立失敗")
                return False

            logger.info("OK: PPSMアソシエーション確立成功（N-SET）")

            # MPPS COMPLETEDデータセット作成
            mpps_dataset = self.create_mpps_completed_dataset()

            # N-SET送信
            logger.info("N-SET（検査終了）送信中...")

            try:
                status = assoc.send_n_set(
                    mpps_dataset,
                    '1.2.840.10008.3.1.2.3.3',  # MPPS SOP Class UID
                    self.mpps_sop_instance_uid
                )

                logger.info(f"N-SET レスポンス詳細:")
                logger.info(f"  Status: {status}")
                logger.info(f"  Type: {type(status)}")

                if status:
                    # pynetdicomのN-SETもtupleで返される: (status_dataset, dataset)
                    if isinstance(status, tuple) and len(status) >= 1:
                        status_ds = status[0]
                        logger.info(f"  Status Dataset: {status_ds}")

                        if hasattr(status_ds, 'Status'):
                            logger.info(f"  Status Code: 0x{status_ds.Status:04X}")
                            if status_ds.Status == 0x0000:
                                logger.info("OK: N-SET（検査終了）成功")
                                success = True
                            else:
                                logger.error(f"N-SET失敗: Status = 0x{status_ds.Status:04X}")
                                success = False
                        else:
                            # Status属性が直接見つからない場合、データセット内を検索
                            if hasattr(status_ds, 'keys') and (0x0000, 0x0900) in status_ds:
                                status_code = status_ds[0x0000, 0x0900].value
                                logger.info(f"  Status Code (from dataset): 0x{status_code:04X}")
                                if status_code == 0x0000:
                                    logger.info("OK: N-SET（検査終了）成功")
                                    success = True
                                else:
                                    logger.error(f"N-SET失敗: Status = 0x{status_code:04X}")
                                    success = False
                            else:
                                logger.error("N-SET失敗: Statusコードが見つかりません")
                                success = False
                    else:
                        logger.error("N-SET失敗: 期待されるtupleレスポンスではありません")
                        success = False
                else:
                    logger.error("N-SET失敗: レスポンスなし")
                    success = False

            except Exception as set_error:
                logger.error(f"N-SET送信エラー: {set_error}")
                success = False

            assoc.release()
            logger.info("アソシエーション終了（N-SET）")

            return success

        except Exception as e:
            logger.error(f"N-SET接続エラー: {e}")
            return False

    def run_mpps_workflow_test(self):
        """MPPS完全ワークフローテスト（検査開始→検査終了）"""
        print("=== MPPS完全ワークフローテスト：検査開始→検査終了 ===")

        # Step 1: 検査開始（N-CREATE）
        print("Step 1: 検査開始（N-CREATE）...")
        create_success = self.test_mpps_in_progress()

        if not create_success:
            print("NG: 検査開始失敗。検査終了はスキップします。")
            return False

        print("OK: 検査開始成功")
        print()

        # 検査実行の模擬（待機）
        print("Step 2: 検査実行中...")
        time.sleep(3)  # 3秒間の検査実行模擬
        print("OK: 検査実行完了")
        print()

        # Step 3: 検査終了（N-SET）
        print("Step 3: 検査終了（N-SET）...")
        set_success = self.test_mpps_completed()

        if not set_success:
            print("NG: 検査終了失敗")
            return False

        print("OK: 検査終了成功")
        print()

        print("OK: MPPS完全ワークフローテスト成功！")
        print(f"   検査開始（N-CREATE）→ 検査実行 → 検査終了（N-SET）が正常に完了しました")
        print(f"   MPPS SOP Instance UID: {self.mpps_sop_instance_uid}")
        print(f"   Study Instance UID: {self.study_instance_uid}")

        return True

def main():
    """メイン実行"""
    print("MPPS統合テスト：Modality Performed Procedure Step")
    print("検査開始（N-CREATE）→ 検査終了（N-SET）ワークフロー")
    print("==========================================")

    client = MPPSTestClient()
    success = client.run_mpps_workflow_test()

    if success:
        print("\\nOK: MPPS統合テスト成功！")
    else:
        print("\\nNG: MPPS統合テスト失敗")

if __name__ == "__main__":
    main()