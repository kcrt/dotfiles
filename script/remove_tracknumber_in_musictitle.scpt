JsOsaDAS1.001.00bplist00�Vscripto� c o n s t   M u s i c   =   A p p l i c a t i o n ( ' M u s i c ' ) ; 
 M u s i c . i n c l u d e S t a n d a r d A d d i t i o n s   =   t r u e ; 
 c o n s t   s e l e c t e d T r a c k s   =   M u s i c . s e l e c t i o n ( ) ; 
 
 l e t   r e s u l t   =   " " ; 
 s e l e c t e d T r a c k s . f o r E a c h ( t r a c k   = >   { 
         l e t   o r i g i n a l N a m e   =   t r a c k . n a m e ( ) ; 
         l e t   n e w N a m e   =   o r i g i n a l N a m e . r e p l a c e ( / ^ \ d + [ _ \ s \ . - ] ? | t r a c k \ d + [ _ \ s \ . - ] ? / g i ,   ' ' ) ; 
 
         / /  Y	f�0L0B0c0_X4T0n00f�T0�f�e� 
         i f   ( n e w N a m e   ! = =   o r i g i n a l N a m e )   { 
                 t r a c k . n a m e   =   n e w N a m e ; 
 	 	 r e s u l t   =   r e s u l t   +   " \ n "   +   o r i g i n a l N a m e   +   "   - >   "   +   n e w N a m e ; 
         } 
 } ) ; 
 
 M u s i c . d i s p l a y D i a l o g ( r e s u l t ) ;                              �jscr  ��ޭ