from typing import Any


class FHIRAdapter:
    """FHIR R4 adapter interface stub.

    Implement mapping from FHIR resources to internal models:
    - MedicationRequest
    - MedicationStatement
    - Observation
    - Patient
    """

    def from_medication_request(self, resource: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def from_medication_statement(self, resource: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def from_observation(self, resource: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def from_patient(self, resource: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
