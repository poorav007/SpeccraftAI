from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ResourceModel1(BaseModel):
    '''Auto-generated Pydantic schema 1 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 1')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate1(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel2(BaseModel):
    '''Auto-generated Pydantic schema 2 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 2')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate2(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel3(BaseModel):
    '''Auto-generated Pydantic schema 3 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 3')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate3(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel4(BaseModel):
    '''Auto-generated Pydantic schema 4 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 4')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate4(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel5(BaseModel):
    '''Auto-generated Pydantic schema 5 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 5')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate5(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel6(BaseModel):
    '''Auto-generated Pydantic schema 6 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 6')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate6(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel7(BaseModel):
    '''Auto-generated Pydantic schema 7 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 7')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate7(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel8(BaseModel):
    '''Auto-generated Pydantic schema 8 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 8')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate8(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel9(BaseModel):
    '''Auto-generated Pydantic schema 9 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 9')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate9(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel10(BaseModel):
    '''Auto-generated Pydantic schema 10 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 10')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate10(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel11(BaseModel):
    '''Auto-generated Pydantic schema 11 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 11')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate11(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel12(BaseModel):
    '''Auto-generated Pydantic schema 12 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 12')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate12(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel13(BaseModel):
    '''Auto-generated Pydantic schema 13 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 13')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate13(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel14(BaseModel):
    '''Auto-generated Pydantic schema 14 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 14')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate14(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel15(BaseModel):
    '''Auto-generated Pydantic schema 15 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 15')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate15(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel16(BaseModel):
    '''Auto-generated Pydantic schema 16 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 16')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate16(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel17(BaseModel):
    '''Auto-generated Pydantic schema 17 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 17')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate17(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel18(BaseModel):
    '''Auto-generated Pydantic schema 18 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 18')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate18(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel19(BaseModel):
    '''Auto-generated Pydantic schema 19 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 19')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate19(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel20(BaseModel):
    '''Auto-generated Pydantic schema 20 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 20')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate20(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel21(BaseModel):
    '''Auto-generated Pydantic schema 21 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 21')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate21(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel22(BaseModel):
    '''Auto-generated Pydantic schema 22 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 22')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate22(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel23(BaseModel):
    '''Auto-generated Pydantic schema 23 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 23')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate23(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel24(BaseModel):
    '''Auto-generated Pydantic schema 24 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 24')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate24(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel25(BaseModel):
    '''Auto-generated Pydantic schema 25 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 25')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate25(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel26(BaseModel):
    '''Auto-generated Pydantic schema 26 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 26')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate26(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel27(BaseModel):
    '''Auto-generated Pydantic schema 27 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 27')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate27(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel28(BaseModel):
    '''Auto-generated Pydantic schema 28 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 28')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate28(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel29(BaseModel):
    '''Auto-generated Pydantic schema 29 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 29')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate29(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel30(BaseModel):
    '''Auto-generated Pydantic schema 30 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 30')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate30(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel31(BaseModel):
    '''Auto-generated Pydantic schema 31 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 31')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate31(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel32(BaseModel):
    '''Auto-generated Pydantic schema 32 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 32')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate32(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel33(BaseModel):
    '''Auto-generated Pydantic schema 33 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 33')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate33(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel34(BaseModel):
    '''Auto-generated Pydantic schema 34 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 34')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate34(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel35(BaseModel):
    '''Auto-generated Pydantic schema 35 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 35')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate35(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel36(BaseModel):
    '''Auto-generated Pydantic schema 36 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 36')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate36(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel37(BaseModel):
    '''Auto-generated Pydantic schema 37 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 37')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate37(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel38(BaseModel):
    '''Auto-generated Pydantic schema 38 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 38')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate38(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel39(BaseModel):
    '''Auto-generated Pydantic schema 39 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 39')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate39(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel40(BaseModel):
    '''Auto-generated Pydantic schema 40 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 40')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate40(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel41(BaseModel):
    '''Auto-generated Pydantic schema 41 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 41')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate41(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel42(BaseModel):
    '''Auto-generated Pydantic schema 42 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 42')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate42(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel43(BaseModel):
    '''Auto-generated Pydantic schema 43 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 43')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate43(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel44(BaseModel):
    '''Auto-generated Pydantic schema 44 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 44')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate44(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel45(BaseModel):
    '''Auto-generated Pydantic schema 45 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 45')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate45(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel46(BaseModel):
    '''Auto-generated Pydantic schema 46 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 46')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate46(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel47(BaseModel):
    '''Auto-generated Pydantic schema 47 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 47')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate47(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel48(BaseModel):
    '''Auto-generated Pydantic schema 48 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 48')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate48(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel49(BaseModel):
    '''Auto-generated Pydantic schema 49 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 49')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate49(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []

class ResourceModel50(BaseModel):
    '''Auto-generated Pydantic schema 50 for 10k-LOC benchmark.'''
    id: int = Field(..., description='Unique ID for resource 50')
    name: str = Field(..., description='Title of item')
    score: float = Field(default=0.0, ge=0.0)
    is_active: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

class ResourceCreate50(BaseModel):
    name: str
    score: float = 0.0
    tags: List[str] = []
