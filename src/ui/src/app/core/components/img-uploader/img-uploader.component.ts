import { Component, EventEmitter, OnDestroy, OnInit, Output } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { FileUploadService } from 'src/app/core/services/file-upload.service';
import { finalize, flatMap, switchMap, tap } from 'rxjs/operators';
import { Observable, of, Subscription } from 'rxjs';

@Component({
  selector: 'app-img-uploader',
  templateUrl: './img-uploader.component.html',
  styleUrls: ['./img-uploader.component.css'],
})
export class ImgUploaderComponent implements OnInit {
  @Output() public word: EventEmitter<string> = new EventEmitter<string>();
  @Output() public isLoading: EventEmitter<boolean> = new EventEmitter<boolean>();

  public form: FormGroup = new FormGroup({});

  private poll$?: Observable<any>;

  constructor(
    private readonly fb: FormBuilder,
    private readonly fileUploadService: FileUploadService,
  ) {
  }

  public ngOnInit(): void {
    this.form = this.fb.group({
      fileSource: [null, Validators.required],
    });
  }

  public onFileChange(event: Event) {
    const files: FileList | null = (<HTMLInputElement>event.target).files;

    this.form.patchValue({ fileSource: files && !!files.length ? files[0] : null });
  }

  public uploadFile(): void {
    const { fileSource } = this.form.getRawValue();

    if (fileSource) {
      this.isLoading.emit(true);
      this.fileUploadService.uploadFile(fileSource)
        .pipe(
          switchMap(({id}) => this.fileUploadService.pollFileDataById(id)),
          finalize(() => this.isLoading.emit(false)),
        )
        .subscribe(word => this.word.emit(word));
    }
  }
}
