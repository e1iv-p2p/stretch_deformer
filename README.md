# stretch_deformer

Lattice based deformer with rollback posibility, for Advanced skeleton setup.
To get correct result you need 'Head_M' joint in scene, or change it by yourself for your purpose in code.
Put this into maya scripts folder.
Then execute:

import  stretch_deformer
from imp import reload 
reload(stretch_deformer)
stretch_deformer.create_ui()







