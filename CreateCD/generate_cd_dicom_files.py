#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CD-R_ROOT配下のDICOMファイル生成スクリプト
integrated_test.pyのDICOM作成機能をベースにしたCD向け構造
"""

import os
import shutil
from datetime import datetime
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import generate_uid
import numpy as np

class CDDicomGenerator:
    """CD-R_ROOT配下にDICOMファイルを生成するクラス"""

    def __init__(self):
        # MODRISPACSと同じImplementation情報を使用
        self.implementation_class_uid = "1.2.392.200036.8120.101.9"
        self.implementation_version = "Monocube1.0.0.0"

        # CD-R_ROOTディレクトリ構造
        self.cd_root = "CD-R_ROOT"
        self.dicom_dir = os.path.join(self.cd_root, "DICOM")

        # 患者・検査・シリーズ情報
        self.patients = [
            {
                "patient_name": "FUKUOKA^CHIHIRO",
                "patient_id": "1234567890",
                "patient_birth_date": "19800502",
                "patient_sex": "M",
                "folder": "PATIENT1"
            },
            {
                "patient_name": "TANAKA^HANAKO",
                "patient_id": "2345678901",
                "patient_birth_date": "19900712",
                "patient_sex": "F",
                "folder": "PATIENT2"
            },
            {
                "patient_name": "SUZUKI^ICHIRO",
                "patient_id": "3456789012",
                "patient_birth_date": "19880925",
                "patient_sex": "M",
                "folder": "PATIENT3"
            }
        ]

    def setup_directory_structure(self):
        """CD-R_ROOT配下のディレクトリ構造を作成"""
        print("CD-R_ROOT配下のディレクトリ構造を作成中...")

        # 既存のCD-R_ROOTディレクトリを削除
        if os.path.exists(self.cd_root):
            shutil.rmtree(self.cd_root)
            print(f"既存の{self.cd_root}ディレクトリを削除")

        # 新しいディレクトリ構造を作成
        os.makedirs(self.dicom_dir, exist_ok=True)

        for patient in self.patients:
            patient_dir = os.path.join(self.dicom_dir, patient["folder"])
            study_dir = os.path.join(patient_dir, "STUDY1")
            series_dir = os.path.join(study_dir, "SERIES1")
            os.makedirs(series_dir, exist_ok=True)

        print(f"ディレクトリ構造作成完了: {self.cd_root}")

        # ディレクトリ構造を表示
        for root, dirs, files in os.walk(self.cd_root):
            level = root.replace(self.cd_root, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            sub_indent = ' ' * 2 * (level + 1)
            for file in files:
                print(f"{sub_indent}{file}")

    def create_secondary_capture_image(self, patient_info, study_uid=None, series_uid=None):
        """Secondary Capture DICOM画像作成（integrated_test.pyベース）"""

        # File Meta Information作成
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.7'  # Secondary Capture
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.ImplementationClassUID = self.implementation_class_uid
        file_meta.ImplementationVersionName = self.implementation_version
        file_meta.TransferSyntaxUID = '1.2.840.10008.1.2'  # Implicit VR Little Endian

        # FileDatasetとして作成
        ds = FileDataset("temp", {}, file_meta=file_meta, preamble=b"\x00" * 128)

        # Patient Module
        ds.PatientName = patient_info["patient_name"]
        ds.PatientID = patient_info["patient_id"]
        ds.PatientBirthDate = patient_info["patient_birth_date"]
        ds.PatientSex = patient_info["patient_sex"]

        # General Study Module
        ds.StudyInstanceUID = study_uid if study_uid else generate_uid()
        ds.StudyDate = datetime.now().strftime("%Y%m%d")
        ds.StudyTime = datetime.now().strftime("%H%M%S")
        ds.ReferringPhysicianName = ""
        ds.StudyID = "1"
        ds.AccessionNumber = f"A{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # General Series Module
        ds.SeriesInstanceUID = series_uid if series_uid else generate_uid()
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
        ds.SecondaryCaptureDeviceManufacturer = "Connect-a-thon 2025"
        ds.SecondaryCaptureDeviceManufacturerModelName = "PDI-CD Generator"

        # Image Pixel Module（16x16の小さなサイズ）
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.Rows = 16
        ds.Columns = 16
        ds.BitsAllocated = 8
        ds.BitsStored = 8
        ds.HighBit = 7
        ds.PixelRepresentation = 0

        # 最小限のピクセルデータ（患者ごとに異なるパターン）
        patient_index = next((i for i, p in enumerate(self.patients) if p["patient_id"] == patient_info["patient_id"]), 0)
        pixel_data = bytearray(16 * 16)
        for i in range(16 * 16):
            # 患者ごとに異なるパターンを生成
            pattern_value = (i + patient_index * 50) % 256
            pixel_data[i] = pattern_value
        ds.PixelData = bytes(pixel_data)

        return ds

    def create_true_color_image(self, patient_info, study_uid=None, series_uid=None):
        """True Color Secondary Capture DICOM画像作成（integrated_test.pyベース）"""

        # File Meta Information作成
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.7'  # Secondary Capture
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.ImplementationClassUID = self.implementation_class_uid
        file_meta.ImplementationVersionName = self.implementation_version
        file_meta.TransferSyntaxUID = '1.2.840.10008.1.2'  # Implicit VR Little Endian

        # FileDatasetとして作成
        ds = FileDataset("temp", {}, file_meta=file_meta, preamble=b"\x00" * 128)

        # Patient Module
        ds.PatientName = patient_info["patient_name"]
        ds.PatientID = patient_info["patient_id"]
        ds.PatientBirthDate = patient_info["patient_birth_date"]
        ds.PatientSex = patient_info["patient_sex"]

        # General Study Module
        ds.StudyInstanceUID = study_uid if study_uid else generate_uid()
        ds.StudyDate = datetime.now().strftime("%Y%m%d")
        ds.StudyTime = datetime.now().strftime("%H%M%S")
        ds.ReferringPhysicianName = ""
        ds.StudyID = "2"
        ds.AccessionNumber = f"B{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # General Series Module
        ds.SeriesInstanceUID = series_uid if series_uid else generate_uid()
        ds.SeriesNumber = "2"
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
        ds.SecondaryCaptureDeviceManufacturer = "Connect-a-thon 2025"
        ds.SecondaryCaptureDeviceManufacturerModelName = "PDI-CD True Color Generator"

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

        # True Color用ピクセルデータ（患者ごとに異なるパターン）
        patient_index = next((i for i, p in enumerate(self.patients) if p["patient_id"] == patient_info["patient_id"]), 0)
        pixel_size = 32 * 32 * 3  # RGB
        pixel_data = bytearray(pixel_size)

        # 患者ごとに異なるカラーパターン
        for y in range(32):
            for x in range(32):
                idx = (y * 32 + x) * 3
                base_offset = patient_index * 64
                pixel_data[idx] = min(255, x * 8 + base_offset)      # R
                pixel_data[idx + 1] = min(255, y * 8 + base_offset // 2)  # G
                pixel_data[idx + 2] = min(255, (x + y) * 4 + base_offset // 3)  # B

        ds.PixelData = bytes(pixel_data)

        return ds

    def generate_dicom_files(self):
        """CD-R_ROOT配下に各種DICOMファイルを生成"""
        print("\\nCD-R_ROOT配下にDICOMファイルを生成中...")

        generated_files = []

        for patient in self.patients:
            patient_dir = os.path.join(self.dicom_dir, patient["folder"])
            study_dir = os.path.join(patient_dir, "STUDY1")
            series_dir = os.path.join(study_dir, "SERIES1")

            print(f"\\n患者: {patient['patient_name']} ({patient['patient_id']})")

            # 同一Study/SeriesのUID生成（同一患者内で統一）
            study_uid = generate_uid()
            series_uid = generate_uid()

            # 1. Secondary Capture画像作成
            print("  Secondary Capture画像作成中...")
            sc_dataset = self.create_secondary_capture_image(patient, study_uid, series_uid)
            sc_file_path = os.path.join(series_dir, "IMAGE1")
            sc_dataset.save_as(sc_file_path, write_like_original=False)
            file_size = os.path.getsize(sc_file_path)
            print(f"  保存完了: {sc_file_path} ({file_size} bytes)")
            generated_files.append(sc_file_path)

            # 2. True Color画像作成（シリーズ2として）
            series2_dir = os.path.join(study_dir, "SERIES2")
            os.makedirs(series2_dir, exist_ok=True)

            print("  True Color画像作成中...")
            tc_dataset = self.create_true_color_image(patient, study_uid, generate_uid())
            tc_file_path = os.path.join(series2_dir, "IMAGE1")
            tc_dataset.save_as(tc_file_path, write_like_original=False)
            file_size = os.path.getsize(tc_file_path)
            print(f"  保存完了: {tc_file_path} ({file_size} bytes)")
            generated_files.append(tc_file_path)

            # ファイル情報を保存
            info_file_path = os.path.join(patient_dir, "file_info.txt")
            with open(info_file_path, 'w', encoding='utf-8') as f:
                f.write(f"Patient Information\\n")
                f.write(f"==================\\n")
                f.write(f"Name: {patient['patient_name']}\\n")
                f.write(f"ID: {patient['patient_id']}\\n")
                f.write(f"Birth Date: {patient['patient_birth_date']}\\n")
                f.write(f"Sex: {patient['patient_sex']}\\n")
                f.write(f"\\nGenerated Files:\\n")
                f.write(f"- Secondary Capture: STUDY1/SERIES1/IMAGE1\\n")
                f.write(f"- True Color: STUDY1/SERIES2/IMAGE1\\n")
                f.write(f"\\nStudy UID: {study_uid}\\n")
                f.write(f"Series 1 UID: {series_uid}\\n")
                f.write(f"\\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")

            print(f"  情報ファイル保存: {info_file_path}")

        return generated_files

    def create_cd_dicomdir(self):
        """CD-R_ROOT用のDICOMDIR作成"""
        print("\\nCD-R_ROOT用DICOMDIR作成中...")

        # まず最初の患者の最初の画像を参照用として読み込み
        ref_file_path = os.path.join(self.dicom_dir, "PATIENT1", "STUDY1", "SERIES1", "IMAGE1")

        if not os.path.exists(ref_file_path):
            print(f"ERROR: 参照ファイルが見つかりません: {ref_file_path}")
            return None

        from pydicom import dcmread
        ref_ds = dcmread(ref_file_path)

        # File Meta Information
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.1.3.10'  # Media Storage Directory Storage
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.TransferSyntaxUID = '1.2.840.10008.1.2'  # Implicit VR Little Endian
        file_meta.ImplementationClassUID = self.implementation_class_uid
        file_meta.ImplementationVersionName = self.implementation_version

        # DICOMDIR Dataset作成
        ds = FileDataset("DICOMDIR", {}, file_meta=file_meta, preamble=b"\x00" * 128)

        # SOP Common Module
        ds.SpecificCharacterSet = 'ISO_IR 100'
        ds.SOPClassUID = '1.2.840.10008.1.3.10'
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID

        # File Set Identification Module
        ds.FileSetID = "CONNECTA2025_CD"
        ds.FileSetDescriptorFileID = "README"
        ds.FileSetConsistencyFlag = 0

        # Directory Information Module
        ds.OffsetOfTheFirstDirectoryRecordOfTheRootDirectoryEntity = 0
        ds.OffsetOfTheLastDirectoryRecordOfTheRootDirectoryEntity = 0

        # Directory Record Sequence（簡潔版 - 全ファイルを参照）
        from pydicom.sequence import Sequence
        records = []

        # 全てのDICOMファイルに対してIMAGE recordを作成
        for patient in self.patients:
            for series_num in ["SERIES1", "SERIES2"]:
                file_path = os.path.join(self.dicom_dir, patient["folder"], "STUDY1", series_num, "IMAGE1")
                if os.path.exists(file_path):
                    try:
                        dicom_ds = dcmread(file_path)

                        # IMAGE Record作成
                        image_record = Dataset()
                        image_record.OffsetOfTheNextDirectoryRecord = 0
                        image_record.RecordInUseFlag = 0xFFFF
                        image_record.OffsetOfReferencedLowerLevelDirectoryEntity = 0
                        image_record.DirectoryRecordType = "IMAGE"

                        # ファイル参照（CD-R_ROOT基準の相対パス）
                        rel_path = os.path.relpath(file_path, self.cd_root).replace(os.sep, '\\\\')
                        path_components = rel_path.split('\\\\')
                        image_record.ReferencedFileID = path_components

                        image_record.ReferencedSOPClassUIDInFile = dicom_ds.SOPClassUID
                        image_record.ReferencedSOPInstanceUIDInFile = dicom_ds.SOPInstanceUID
                        image_record.ReferencedTransferSyntaxUIDInFile = '1.2.840.10008.1.2'

                        if hasattr(dicom_ds, 'InstanceNumber'):
                            image_record.InstanceNumber = dicom_ds.InstanceNumber

                        records.append(image_record)
                        print(f"  IMAGE Record追加: {'/'.join(path_components)}")

                    except Exception as e:
                        print(f"  WARNING: {file_path}の読み込みエラー: {e}")

        ds.DirectoryRecordSequence = Sequence(records)

        # DICOMDIR保存
        dicomdir_path = os.path.join(self.cd_root, "DICOMDIR")
        ds.save_as(dicomdir_path, write_like_original=False)

        file_size = os.path.getsize(dicomdir_path)
        print(f"DICOMDIR作成完了: {dicomdir_path} ({file_size} bytes)")
        print(f"参照ファイル数: {len(records)}")

        return dicomdir_path

    def create_readme_file(self):
        """README.TXTファイル作成"""
        print("\\nREADME.TXT作成中...")

        readme_path = os.path.join(self.cd_root, "README.TXT")

        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write("Connect-a-thon 2025 - Portable Data for Imaging (PDI) CD\\n")
            f.write("=" * 60 + "\\n")
            f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
            f.write("\\n")
            f.write("DICOM Conformance Statement\\n")
            f.write("-" * 30 + "\\n")
            f.write(f"Implementation Class UID: {self.implementation_class_uid}\\n")
            f.write(f"Implementation Version: {self.implementation_version}\\n")
            f.write("Transfer Syntax: Implicit VR Little Endian (1.2.840.10008.1.2)\\n")
            f.write("Character Set: ISO_IR 100\\n")
            f.write("\\n")
            f.write("Directory Structure\\n")
            f.write("-" * 20 + "\\n")
            f.write("CD-R_ROOT/\\n")
            f.write("├── DICOMDIR\\n")
            f.write("├── README.TXT\\n")
            f.write("└── DICOM/\\n")

            for patient in self.patients:
                f.write(f"    ├── {patient['folder']}/\\n")
                f.write("    │   ├── file_info.txt\\n")
                f.write("    │   └── STUDY1/\\n")
                f.write("    │       ├── SERIES1/\\n")
                f.write("    │       │   └── IMAGE1 (Secondary Capture)\\n")
                f.write("    │       └── SERIES2/\\n")
                f.write("    │           └── IMAGE1 (True Color)\\n")

            f.write("\\n")
            f.write("Patient Information\\n")
            f.write("-" * 20 + "\\n")

            for patient in self.patients:
                f.write(f"- {patient['patient_name']} (ID: {patient['patient_id']})\\n")
                f.write(f"  Birth: {patient['patient_birth_date']}, Sex: {patient['patient_sex']}\\n")

            f.write("\\n")
            f.write("DICOM Image Types\\n")
            f.write("-" * 18 + "\\n")
            f.write("- Secondary Capture Image Storage (1.2.840.10008.5.1.4.1.1.7)\\n")
            f.write("  Monochrome 16x16, 8-bit\\n")
            f.write("- True Color Secondary Capture\\n")
            f.write("  RGB 32x32, 8-bit per channel\\n")
            f.write("\\n")
            f.write("Usage Instructions\\n")
            f.write("-" * 19 + "\\n")
            f.write("1. Insert CD into DICOM-compatible workstation\\n")
            f.write("2. Open DICOMDIR file\\n")
            f.write("3. Navigate patient/study/series structure\\n")
            f.write("4. View individual DICOM images\\n")
            f.write("\\n")
            f.write("Technical Notes\\n")
            f.write("-" * 15 + "\\n")
            f.write("- All files comply with DICOM Part 10 format\\n")
            f.write("- DICOMDIR follows Media Storage Directory Storage\\n")
            f.write("- Compatible with standard DICOM viewers\\n")
            f.write("- Hierarchical directory structure for optimal organization\\n")

        print(f"README.TXT作成完了: {readme_path}")
        return readme_path

def main():
    """メイン実行関数"""
    print("Connect-a-thon 2025 - CD-R_ROOT DICOM生成スクリプト")
    print("integrated_test.pyベースの構造を使用")
    print("=" * 60)

    generator = CDDicomGenerator()

    try:
        # Step 1: ディレクトリ構造作成
        generator.setup_directory_structure()

        # Step 2: DICOMファイル生成
        generated_files = generator.generate_dicom_files()

        # Step 3: DICOMDIR作成
        dicomdir_path = generator.create_cd_dicomdir()

        # Step 4: README作成
        readme_path = generator.create_readme_file()

        print("\\n" + "=" * 60)
        print("CD-R_ROOT生成完了")
        print("=" * 60)
        print(f"生成されたDICOMファイル数: {len(generated_files)}")
        print(f"DICOMDIR: {dicomdir_path}")
        print(f"README: {readme_path}")

        print("\\n生成されたファイル:")
        for file_path in generated_files:
            file_size = os.path.getsize(file_path)
            rel_path = os.path.relpath(file_path)
            print(f"  {rel_path} ({file_size} bytes)")

        print("\\n✅ CD-R_ROOT構造の完成")
        print("✅ Connect-a-thon 2025対応PDI-CD ready!")

    except Exception as e:
        print(f"\\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()