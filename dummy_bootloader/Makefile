all: dummy_bootloader

dummy_bootloader: dummy_bootloader.S
	nasm $< -o $@

testbootdisk: dummy_bootloader
	$(shell dd if=/dev/zero of=testbootdisk bs=512 count=2880)

run: testbootdisk
	$(shell dd if=dummy_bootloader of=testbootdisk conv=notrunc)
	$(shell qemu -fda testbootdisk -boot a)

clean:
	rm -f dummy_bootloader
	rm -f testbootdisk

.phony: all run clean
