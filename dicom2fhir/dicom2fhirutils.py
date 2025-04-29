from datetime import datetime, date
import typing

from fhir.resources import imagingstudy
from fhir.resources import identifier
from fhir.resources import codeableconcept
from fhir.resources import codeablereference
from fhir.resources import coding
from fhir.resources import patient
from fhir.resources import humanname
from fhir.resources import reference

TERMINOLOGY_CODING_SYS = "http://terminology.hl7.org/CodeSystem/v2-0203"
TERMINOLOGY_CODING_SYS_CODE_ACCESSION = "ACSN"
TERMINOLOGY_CODING_SYS_CODE_MRN = "MR"

ACQUISITION_MODALITY_SYS = "http://dicom.nema.org/resources/ontology/DCM"

SOP_CLASS_SYS = "urn:ietf:rfc:3986"


def gen_accession_identifier(id):
    idf = identifier.Identifier()
    idf.use = "usual"
    idf.type = codeableconcept.CodeableConcept()
    idf.type.coding = []
    acsn = coding.Coding()
    acsn.system = TERMINOLOGY_CODING_SYS
    acsn.code = TERMINOLOGY_CODING_SYS_CODE_ACCESSION

    idf.type.coding.append(acsn)
    idf.value = id
    return idf


def gen_studyinstanceuid_identifier(id):
    idf = identifier.Identifier()
    idf.system = "urn:dicom:uid"
    idf.value = "urn:oid:" + id
    return idf


def get_patient_resource_ids(PatientID, IssuerOfPatientID):
    idf = identifier.Identifier()
    idf.use = "usual"
    idf.value = PatientID

    idf.type = codeableconcept.CodeableConcept()
    idf.type.coding = []
    id_coding = coding.Coding()
    id_coding.system = TERMINOLOGY_CODING_SYS
    id_coding.code = TERMINOLOGY_CODING_SYS_CODE_MRN
    idf.type.coding.append(id_coding)

    if IssuerOfPatientID is not None:
        idf.assigner = reference.Reference()
        idf.assigner.display = IssuerOfPatientID

    return idf


def calc_gender(gender):
    if gender is None:
        return "unknown"
    if not gender:
        return "unknown"
    if gender.upper().lower() == "f":
        return "female"
    if gender.upper().lower() == "m":
        return "male"
    if gender.upper().lower() == "o":
        return "other"

    return "unknown"


# def calc_dob(dicom_dob):
#     if dicom_dob == '':
#         return None

#     fhir_dob = fhirdate.FHIRDate()
#     try:
#         dob = datetime.strptime(dicom_dob, '%Y%m%d')
#         fhir_dob.date = dob
#     except Exception:
#         return None
#     return fhir_dob


def inline_patient_resource(referenceId, PatientID, IssuerOfPatientID, patientName, gender, dob):
    p = patient.Patient.model_construct()
    p.id = referenceId
    p.name = []
    p.identifier = [get_patient_resource_ids(PatientID, IssuerOfPatientID)]
    hn = humanname.HumanName.model_construct()
    hn.family = patientName.family_name
    hn.given = [patientName.given_name]
    p.name.append(hn)
    p.gender = calc_gender(gender)
    p.birthDate = datetime.strptime(dob, '%Y%m%d').date()
    p.active = True
    return p


def gen_procedurecode_array(procedures) -> typing.List[codeablereference.CodeableReference] | None:
    if procedures is None:
        return None
    fhir_proc = []
    for p in procedures:
        concept = codeableconcept.CodeableConcept.model_construct()
        c = coding.Coding()
        c.system = p["system"]
        c.code = p["code"]
        c.display = p["display"]
        concept.coding = []
        concept.coding.append(c)
        concept.text = p["display"]
        fhir_proc.append(codeablereference.CodeableReference(concept=concept))
    if len(fhir_proc) > 0:
        return fhir_proc
    return None


def gen_started_datetime(dt, tm) -> datetime | date | None:
    if dt is None:
        return None

    fhirDtm = datetime.strptime(dt, '%Y%m%d').date()
    if tm is None or len(tm) < 6:
        return fhirDtm
    
    studytm = datetime.strptime(tm[0:6], '%H%M%S')
    # SEE: https://build.fhir.org/datatypes.html#dateTime
    # In FHIR dateTime type documentation it says that:
    # 'if hours and minutes are specified, a timezone offset SHALL be populated'
    # So we need to set the timezone offset in the future to be compatible with FHIR
    fhirDtm = datetime.combine(fhirDtm, studytm.time())
    return fhirDtm


def gen_reason(reason, reasonStr) -> typing.List[codeablereference.CodeableReference] | None:
    if reason is None and reasonStr is None:
        return None
    reasonList = []
    if reason is None or len(reason) <= 0:
        rc = codeableconcept.CodeableConcept()
        rc.text = reasonStr
        reasonList.append(rc)
        return reasonList

    for r in reason:
        rc = codeableconcept.CodeableConcept()
        rc.coding = []
        c = coding.Coding()
        c.system = r["system"]
        c.code = r["code"]
        c.display = r["display"]
        rc.coding.append(c)
        reasonList.append(codeablereference.CodeableReference(concept=rc))
    return reasonList


# def gen_modality_coding(mod):
#     c = coding.Coding()
#     c.system = ACQUISITION_MODALITY_SYS
#     c.code = mod
#     return c


def gen_modality_coding(mod):
    rc = codeableconcept.CodeableConcept.model_construct()
    rc.coding = []
    c = coding.Coding()
    c.system = ACQUISITION_MODALITY_SYS
    c.code = mod
    rc.coding.append(c)
    return rc


def update_study_modality_list(study: imagingstudy.ImagingStudy, modality: codeableconcept.CodeableConcept):
    if study.modality is None or len(study.modality) <= 0:
        study.modality = []
        study.modality.append(modality)
        return

    c = next((mc for mc in study.modality if mc.coding == modality.coding), None)
    if c is not None:
        return

    study.modality.append(modality)
    return


def gen_instance_sopclass(SOPClassUID):
    c = coding.Coding()
    c.system = SOP_CLASS_SYS
    c.code = "urn:oid:" + SOPClassUID
    return c


def gen_coding_text_only(text):
    c = coding.Coding()
    c.code = text
    c.userSelected = True
    return c


def dcm_coded_concept(CodeSequence):
    concepts = []
    for seq in CodeSequence:
        concept = {}
        concept["code"] = seq[0x0008, 0x0100].value
        concept["system"] = seq[0x0008, 0x0102].value
        concept["display"] = seq[0x0008, 0x0104].value
        concepts.append(concept)
    return concepts
