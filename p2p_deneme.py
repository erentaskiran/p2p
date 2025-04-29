import os

CHUNK_SIZE = 128*1024

def split_file(file_path: str, output_folder: str, chunk_size: int = 128):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    with open(file_path, "rb") as file:
        chunk_index = 0
        while True:
            chunk = file.read(CHUNK_SIZE)
            if not chunk:
                break

            chunk_filename = os.path.join(output_folder, f"chunk_{chunk_index}.part")
            with open(chunk_filename,"wb") as chunk_file:
                chunk_file.write(chunk)

            print(f"Created: {chunk_filename}")
            chunk_index += 1

test_file_path = "test_file.txt"
with open(test_file_path, "w") as f:
    f.write("merhaba " * 15000)

    output_folder = "chunks"

    split_file(test_file_path,output_folder)

def merge_files(input_folder: str, output_file_path: str):
    with open(output_file_path, "wb") as output_file:
        chunk_index = 0
        while True:
            chunk_filename = os.path.join(input_folder, f"chunk_{chunk_index}.part")
            if not os.path.exists(chunk_filename):
                break  # Eğer sıradaki parça yoksa birleşmeyi bitir

            with open(chunk_filename, "rb") as chunk_file:
                output_file.write(chunk_file.read())

            print(f"Merged: {chunk_filename}")
            chunk_index += 1


# Merge işlemi
merged_file_path = "merged_test_file.txt"
merge_files(output_folder, merged_file_path)

def compare_files(file1_path: str, file2_path: str):
    with open(file1_path, "rb") as file1, open(file2_path, "rb") as file2:
        file1_content = file1.read()
        file2_content = file2.read()

        if file1_content == file2_content:
            print("Dosyalar birebir aynı!")
        else:
            print("Dosyalar farklı!")

# Testi çalıştır
compare_files("test_file.txt", "merged_test_file.txt")

