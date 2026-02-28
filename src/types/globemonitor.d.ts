declare module '@worldmonitor' {
  export class App {
    constructor(containerId: string);
    init(): Promise<void>;
  }
}

declare module '@worldmonitor-css';
