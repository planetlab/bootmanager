SCREEN_COLS     equ 80
SCREEN_ROWS     equ 25
STACK_SEGMENT   equ 09000h	; top of memory
STACK_SIZE      equ 00fffh	; 4K - 1 bytes of stack
	
TEXT_COLOR	equ 0x07	; white on black

	jmp 07c0h:start

message		db "PlanetLab nodes require a boot cd at all times to function.",0
	
start:
	mov ax, cs
	mov ds, ax
	mov es, ax
	
	mov sp, STACK_SEGMENT	; setup stack (not really used)
	mov ss, sp
	mov sp, STACK_SIZE

	;; clear out the screen, using the scroll down bios int.
	mov ah, 0x07		; for int 0x10, 0x07 is scroll down window
	mov al, 0 		; entire window
	mov cx, 0		; upper left corner = (0,0)
	mov dh, SCREEN_ROWS	; row of bottom
	mov dl,	SCREEN_COLS	; column of right
	mov bh, 7
	int 10h			
	
	mov si, message

strout: lodsb
	cmp al, 0
	je done
	mov ah, 0x0E		; for int 0x10, 0xOE is char out
	mov bx, TEXT_COLOR
	int 0x10
	jmp strout

done:	
	jmp done
	
	times 510 - ($ - $$) db 0 ;  last two bytes are magic for x86 boot sectors
	dw 0aa55h
