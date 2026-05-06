from datetime import datetime, timezone
from pydantic import BaseModel, field_serializer

class BaseSchema(BaseModel):
    @field_serializer(datetime)
    def serialize_dt(self, dt: datetime, _info):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
        return dt.isoformat().replace('+00:00', 'Z')
